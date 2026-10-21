from typing import Literal, List
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from backend.Agents.Common_State import State
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
load_dotenv()

OPENAI_API_KEY=os.getenv('OPENAI_API_KEY')

llm=ChatOpenAI(api_key=OPENAI_API_KEY, model='gpt-4o-mini')

#how many earlier messages the orchestrator sees, so follow ups like "do the same for Rahul" can be routed
HISTORY_WINDOW = 10

Agent_Name = Literal['Email_agent', 'Meet_scheduler_agent', 'PDF_agent', 'Search_agent', 'Task_assign_agent', 'General_agent']

class Step(BaseModel):
        agent: Agent_Name = Field(description="Name of the agent that runs this step")
        instruction: str = Field(description="Clear, detailed instruction for this agent including all extracted inputs required to perform the step")

class Orchestration_Outline(BaseModel):
        steps: List[Step] = Field(description="Ordered steps, one per agent call. Usually one step; several when the user asks for several actions")


async def Orchestrator_Agent(state : State):
        print('Orchestration agent called')
        message=state['messages'][-1].content

        recent_history=''
        for msg in state['messages'][-HISTORY_WINDOW-1:-1]:
                if isinstance(msg, HumanMessage):
                        recent_history+=f"{msg.additional_kwargs.get('username', 'Human')} : {msg.content}\n"
                elif isinstance(msg, AIMessage) and msg.content:
                        recent_history+=f"Assistant : {msg.content}\n"

        instruction=f'''
You are an orchestrator agent. Your job is to:
1. Identify the user's intent
2. Split it into one or more steps, in the order they must run
3. Select the most appropriate agent for each step
4. Generate a COMPLETE instruction for each step

## Available agents

1. Email_agent — send/draft emails
2. Meet_scheduler_agent — schedule meetings/events
3. PDF_agent — generate summaries or PDFs
4. Search_agent — search external information
5. Task_assign_agent — break ideas into tasks
6. General_agent — handle general queries

## Your Output MUST include:
- steps → ordered list, each with
  - agent → the selected agent (exact name)
  - instruction → a fully detailed instruction for that agent

## IMPORTANT RULES

- Extract ALL relevant details from the user message
- Use the recent conversation to resolve references like "him", "the same", "that project"
- If something is missing, make reasonable assumptions (do NOT ask questions)
- Make each instruction directly executable by its agent
- Be specific and structured

## Multiple steps

- Most requests need exactly ONE step
- Create several steps only when the user clearly asks for several different actions
  (e.g. "search X and email the summary to John" → Search_agent, then Email_agent)
- Order steps so that a step comes after any step whose output it needs
- A later step automatically receives the results of earlier steps, so its instruction can
  refer to them (e.g. "Email John a summary of the search results")
- Never repeat the same action in two steps

## What "good instruction" means

Each agent should receive:
- clear goal
- required inputs
- expected output format

---

## Agent-specific expectations

### Email_agent
Include:
- recipient
- subject (generate if missing)
- email body (clear and professional)

### Meet_scheduler_agent
Include:
- participants
- date & time
- duration (default 30 mins if missing)
- agenda (if possible)

### PDF_agent
Include:
- to create a insight report/PDF of the project being discussed
- format (brief/detailed)
- title if relevant

### Search_agent
Include:
- refined search query
- what kind of information is needed

### Task_assign_agent
Include:
- project/idea
- break into actionable tasks
- include priorities or sequence
- assign work to team members

### General_agent
Include:
- clear explanation request

---

## Output format (STRICT)

Return ONLY:

{{
  "steps": [
    {{"agent": "<agent_name>", "instruction": "<detailed instruction>"}}
  ]
}}

---

## Examples

User: "Email John the project update and tell him we are delayed"

Output:
{{
  "steps": [
    {{"agent": "Email_agent", "instruction": "Write a professional email to John informing him that the project is delayed. Include an apology, current status, and expected revised timeline. Generate a suitable subject line."}}
  ]
}}

User: "Find the latest LangGraph release and email a short summary to Priya"

Output:
{{
  "steps": [
    {{"agent": "Search_agent", "instruction": "Latest LangGraph release version, release date and key new features"}},
    {{"agent": "Email_agent", "instruction": "Write a short professional email to Priya summarising the latest LangGraph release using the search results from the previous step. Generate a suitable subject line."}}
  ]
}}

---

Recent conversation (oldest first):
{recent_history or 'None'}

User message:
{message}
'''

        structure_llm=llm.with_structured_output(Orchestration_Outline)
        response=await structure_llm.ainvoke([SystemMessage(content=instruction), HumanMessage(content=message)])

        plan=[step.model_dump() for step in response.steps]
        if not plan:
                plan=[{'agent': 'General_agent', 'instruction': message}]
        print(f'[Orchestrator] plan: {plan}')

        #starting a fresh run, results of the previous @ai run are cleared
        return {
                'plan' : plan,
                'step_results' : None
        }