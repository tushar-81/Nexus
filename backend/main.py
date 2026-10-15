from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend.Graph import build_graph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from backend.Agents.Common_State import State
from langgraph.types import Command, interrupt
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

node_display_names = {
    'Orchestrator':     'Orchestrator',
    'Email_Content':    'Email Agent',
    'HITL_Email':       'Email Review',
    'Send_Email':       'Sending Email',
    'Schedule_Meeting': 'Meeting Scheduler',
    'Create_Meet':      'Creating Meeting',
    'HITL_Meet':        'Meeting Review',
    'PDF_Report':       'Analysing Discussion',
    'PDF_create':       'Generating Report',
    'Search':           'Searching Web',
    'Get_Members':      'Fetching Members',
    'Extract_Tasks':    'Extracting Tasks',
    'HITL_Trello':      'Board Review',
    'Trello':           'Creating Trello Board',
    'General':          'General Agent',
    '__interrupt__':    'Waiting for approval',
}

result = None
interrupt_found = False

class WebSocket_Manager:
    def __init__(self) -> None:
        self.active_websocket_clients=[]

    async def Connect(self, websocket : WebSocket):
        await websocket.accept()
        self.active_websocket_clients.append(websocket)

    def disconnect(self, websocket : WebSocket):
        if websocket in self.active_websocket_clients:
            self.active_websocket_clients.remove(websocket)

    async def broadcast(self, message : dict):
        for conn in list(self.active_websocket_clients):
            try:
                await conn.send_json(message)
            except Exception:
                #client already gone (closed tab / server reload), dropping it
                self.disconnect(conn)


graph = None

@asynccontextmanager
async def lifespan(app : FastAPI):
    #conversation history is persisted in checkpoints.db so it survives restarts
    global graph
    async with AsyncSqliteSaver.from_conn_string('checkpoints.db') as checkpointer:
        graph = build_graph(checkpointer)
        yield

app=FastAPI(lifespan=lifespan)
manager=WebSocket_Manager()

app.mount("/static", StaticFiles(directory="static"), name="static")

config = {'configurable': {'thread_id': 'Nexus'}}

HISTORY_LIMIT = 100

async def get_pending_interrupt():
    #approval waiting in the saved graph state, it survives page reloads and server restarts
    snapshot = await graph.aget_state(config)
    return snapshot.interrupts[0].value if snapshot.interrupts else None

async def send_history(websocket : WebSocket):
    #sending the saved conversation from checkpoints.db so a page reload does not lose the chat
    snapshot = await graph.aget_state(config)
    history = []
    last_time = None
    for message in snapshot.values.get('messages', [])[-HISTORY_LIMIT:]:
        #AI replies have no timestamp, they take the time of the message they answered
        last_time = message.additional_kwargs.get('time', last_time)
        if isinstance(message, HumanMessage):
            history.append({'role': 'human', 'username': message.additional_kwargs.get('username', 'Member'), 'text': message.content, 'time': last_time})
        elif isinstance(message, AIMessage) and message.content:
            history.append({'role': 'AI', 'text': message.content, 'time': last_time})

    await websocket.send_json({'type': 'history', 'messages': history})

    #reopening a review that was still waiting when the page was reloaded
    if snapshot.interrupts:
        interrupt_data = snapshot.interrupts[0].value
        await websocket.send_json({'type': 'interrupt', 'subtype': interrupt_data.get('type'), 'data': interrupt_data, 'restored': True})

@app.get("/")
async def serve_frontend():
    return FileResponse("./frontend/nexus.html")


@app.websocket('/ws')
async def Websocket_Chat(websocket : WebSocket):
    await manager.Connect(websocket=websocket)
    try:
        await send_history(websocket)
        while True:
            #receiving message from websocket client
            data = await websocket.receive_json()
            #review panel answers carry 'response', chat messages carry 'text'
            if 'response' not in data:
                username= data.get('username') or 'Anonymous'
                user_message = (data.get('text') or '').strip()
                if not user_message:
                    continue

                #a review is still waiting, showing it again instead of starting a new run
                pending = await get_pending_interrupt()
                if pending:
                    await websocket.send_json({'type': 'system', 'message': 'Finish the pending review first'})
                    await websocket.send_json({'type': 'interrupt', 'subtype': pending.get('type'), 'data': pending})
                    continue

            #displaying this message to all the other websocket clients
                await manager.broadcast(
                {
                    'role' : 'human',
                    'username' : username,
                    'text' : user_message
                })

                defined_state = {
                "messages": [HumanMessage(content=user_message, additional_kwargs={'username': username, 'time': datetime.now().astimezone().isoformat()})],
                'sender_address' : 'tusharbailwal81@gmail.com',
                #tusharbailwal is a real Trello member (gets assigned), the others are demo members (get a name label on the card)
                'members_list' :  [{'username' : 'tusharbailwal', 'name' : 'Tushar', 'member_role': 'Manager'}, {'username' : 'shivam', 'name' : 'Shivam', 'member_role': 'AI Engineer'},{'username' : 'priya', 'name' : 'Priya', 'member_role': 'Backend Developer'},{'username' : 'rahul', 'name' : 'Rahul', 'member_role': 'Marketing'}],
                'board_name' :  'Nexus'}

                try:
                    result = None
                    interrupt_found = False

                    async for chunk in graph.astream(defined_state, config, stream_mode='updates'):
                        
                        print(f"[STREAM CHUNK] keys: {list(chunk.keys())}")
                        print(f"[STREAM CHUNK] full: {chunk}")
                        node_name = list(chunk.keys())[0]

                        if '__interrupt__' in chunk or any('__interrupt__' in str(v) for v in chunk.values()):
                            interrupt_data = chunk['__interrupt__'][0].value
                            type_agent = interrupt_data.get('type')

                            await manager.broadcast({
                                'type': 'node_update',
                                'node': node_display_names.get(node_name, node_name),
                            'status': 'waiting'})

                            await manager.broadcast({
                                'type': 'interrupt',
                                'subtype': type_agent,
                                'data': interrupt_data
                            })
                            interrupt_found = True
                            break

                        display = node_display_names.get(node_name, node_name)
                        await manager.broadcast({
                            'type': 'node_update',
                            'node': display,
                            'status': 'done'
                        })
                        result = chunk[node_name]

                        if not interrupt_found and result:
                            messages = result.get('messages', [])
                            last_msg = messages[-1] if messages else None
                            if last_msg and isinstance(last_msg, AIMessage):
                                await manager.broadcast({'role': 'AI', 'text': last_msg.content})
                            await manager.broadcast({'type': 'node_clear'})

                except Exception as e:
                    await manager.broadcast({"type": "error", "message": str(e)})
                continue
            
            else:
                data_response=data.get('response')
                print(f"[Resume] data_response: {data_response}")

                #the review may already be handled (another tab, or a panel left open from before)
                if not await get_pending_interrupt():
                    await websocket.send_json({"type": "close_interrupt"})
                    await websocket.send_json({'type': 'system', 'message': 'Nothing is waiting for approval'})
                    continue

                #remembering the last message already shown, so it is not broadcast again after resume
                state_before = await graph.aget_state(config)
                messages_before = state_before.values.get('messages', [])
                last_id_before = messages_before[-1].id if messages_before else None

                try:
                    result_after=await graph.ainvoke(Command(resume=data_response), config)
                except Exception as e:
                    await manager.broadcast({"type": "close_interrupt"})
                    await manager.broadcast({"type": "error", "message": str(e)})
                    continue

                await manager.broadcast({"type": "close_interrupt"})

                if "__interrupt__" in result_after:
                    interrupt_data = result_after["__interrupt__"][0].value

                    await manager.broadcast({
                        "type": "interrupt",
                        "subtype": interrupt_data.get('type'),
                        "data": interrupt_data
                    })
                    continue
                
                messages_after = result_after.get('messages') or []
                if messages_after and messages_after[-1].id != last_id_before:
                    await manager.broadcast(
                            {
                                'role' : 'AI',
                                'messages' : messages_after[-1].content
                            }
                        )
                continue
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)