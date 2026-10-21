from backend.Agents.Common_State import State
from backend.Agents.Assign_task import Board_members_list, Extract_tasks, human_review, Trello_agent
from backend.Agents.Email_agent import Email_agent, review_node, send_email
from backend.Agents.general_agent import general_agent
from backend.Agents.Meet_scheduler_agent import Scheduler_Agent, create_meeting, review_meeting
from backend.Agents.PDF_create import Agent1, Agent2
from backend.Agents.Search_Agent import Search_agent
from backend.Agents.Orchestrator_Agent import Orchestrator_Agent
from backend.Agents.Dispatcher import Dispatcher
from backend.condition_edge import Pass_AI, dispatcher_function
from langgraph.graph.state import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

def build_graph(checkpointer):
    builder=StateGraph(State)

#Main Agent - Orchestratr agent
    builder.add_node('Orchestrator', Orchestrator_Agent)

#runs the orchestrator's plan one step at a time, every agent comes back here when it finishes
    builder.add_node('Dispatcher', Dispatcher)

#Assign tasks - trello
    builder.add_node('Get_Members', Board_members_list)
    builder.add_node('Extract_Tasks', Extract_tasks)
    builder.add_node('HITL_Trello', human_review)
    builder.add_node('Trello', Trello_agent)

#Email 
    builder.add_node('Email_Content', Email_agent)
    builder.add_node('HITL_Email', review_node)
    builder.add_node('Send_Email', send_email)

# general 
    builder.add_node('General', general_agent)

#Google meet scheduler
    builder.add_node('Schedule_Meeting', Scheduler_Agent)
    builder.add_node('Create_Meet', create_meeting)
    builder.add_node('HITL_Meet', review_meeting)

#PDF or report
    builder.add_node('PDF_Report', Agent1)
    builder.add_node('PDF_create', Agent2)

#Search Web
    builder.add_node('Search', Search_agent)

    builder.add_conditional_edges(
        START,
        Pass_AI,
        {
            'AI' : 'Orchestrator',
            'CHAT' : END
        }
    )

    builder.add_edge('Orchestrator', 'Dispatcher')

    builder.add_conditional_edges(
        'Dispatcher',
        dispatcher_function,
        {
            'Email_agent': 'Email_Content',
            'Meet_scheduler_agent' : 'Schedule_Meeting',
            'PDF_agent' : 'PDF_Report',
            'Search_agent' : 'Search',
            'Task_assign_agent' : 'Get_Members',
            'General_agent' : 'General',
            'DONE' : END
        }
    )

#Email flow
    builder.add_edge('Email_Content', 'HITL_Email')
    builder.add_edge('Send_Email', 'Dispatcher')

#Meet - review first, the calendar event is only created after approval
    builder.add_edge('Schedule_Meeting', 'HITL_Meet')
    builder.add_edge('Create_Meet', 'Dispatcher')

#PDF
    builder.add_edge('PDF_Report', 'PDF_create')
    builder.add_edge('PDF_create', 'Dispatcher')

#Search
    builder.add_edge('Search', 'Dispatcher')

#Trello
    builder.add_edge('Get_Members', 'Extract_Tasks')
    builder.add_edge('Extract_Tasks', 'HITL_Trello')
    builder.add_edge('Trello', 'Dispatcher')

#General
    builder.add_edge('General', 'Dispatcher')


    graph=builder.compile(checkpointer=checkpointer)

    return graph


