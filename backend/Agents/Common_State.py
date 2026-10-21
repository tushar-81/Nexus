from typing import TypedDict, Annotated, Optional
from typing import List
import base64
from langgraph.graph.message import add_messages, BaseMessage
from langchain_core.messages import HumanMessage

def merge_step_results(old, new):
    #None clears the list (new @ai run), a list gets appended
    if new is None:
        return []
    return (old or []) + new

def last_user_message(state) -> str:
    #the @ai message that started this run, messages[-1] can be an earlier step's AI reply
    for message in reversed(state.get('messages', [])):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ''

class State(TypedDict):
    messages : Annotated[list[BaseMessage], add_messages]

    Ai_trigger : Optional[bool]

    #LLM output for agent
    LLM_instruction : Optional[str]
    next : Optional[str]

    #Multi agent plan - steps still to run, and short outputs of the finished steps
    plan : Optional[list[dict]] #{'agent', 'instruction'}
    step_results : Annotated[list[str], merge_step_results]

    ## PDF
    pdf_bytes : Optional[bytes]
    pdf_html : Optional[str]
    pdf_base64 : Optional[str]
    PDF_feedback : Optional[str]
    Agent1Output : Optional[dict]

    #Google Meet
    Meet_dict : Optional[dict]
    Meet_link : Optional[str]
    Meet_feedback : Optional[str]
    Last_Scheduler_Agent_output : Optional[str]

    #Email Agent
    sender_address : Optional[str]
    Email_Feedback: Optional[str]
    to_email : Optional[list[str]]
    cc_email : Optional[list[str]]
    bcc_email : Optional[list[str]]
    subject : Optional[str]
    body : Optional[str]
    email_status : Optional[str]

    #Trello Details
    board_name : str
    board_id : str
    members_list : list[dict] #{'member_name, member_role, member_trello}
    board_outline : Optional[dict]
    Board_feedback : Optional[str]