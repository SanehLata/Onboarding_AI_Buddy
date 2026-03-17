# Entry point

from graph import onboarding_graph, create_initial_state, process_message

# On session start
state = create_initial_state()

# On each user message
response, state = process_message(state, user_input)