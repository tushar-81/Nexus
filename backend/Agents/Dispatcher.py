from backend.Agents.Common_State import State

#long outputs (search answers) are cut so later prompts stay small
RESULT_CHAR_LIMIT = 3000

#agents whose instruction is used as-is (Search sends it to the search engine as the query)
NO_CONTEXT_AGENTS = {'Search_agent'}


def Dispatcher(state : State):
    plan = state.get('plan') or []

    if not plan:
        print('[Dispatcher] plan finished')
        return {'next': 'DONE'}

    step, remaining = plan[0], plan[1:]
    agent = step.get('agent')
    instruction = step.get('instruction', '')

    results = state.get('step_results') or []
    if results and agent not in NO_CONTEXT_AGENTS:
        earlier = '\n'.join(f'{i+1}. {result[:RESULT_CHAR_LIMIT]}' for i, result in enumerate(results))
        instruction = f"{instruction}\n\nResults of the earlier steps (use them where relevant):\n{earlier}"

    print(f'[Dispatcher] next step: {agent}, {len(remaining)} left')

    return {
        'plan': remaining,
        'next': agent,
        'LLM_instruction': instruction,

        #clearing per step fields, so a step does not see the feedback/draft of an earlier run
        'Email_Feedback': None,
        'subject': '',
        'body': '',
        'Meet_feedback': '',
        'Last_Scheduler_Agent_output': None,
        'Board_feedback': '',
        'board_outline': None,
    }
