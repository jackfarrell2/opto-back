from pulp import LpMaximize, LpProblem, LpVariable, lpSum

def optimize_lineup(player_data, max_total_salary=50000):
    num_players = 8
    position_slots = ['F', 'C', 'G', 'SG', 'PG', 'SF', 'PF', 'UTIL']
    meta_players = {}
    # Separate each player into each position they are eligible for
    for player in player_data:
        meta_player = player.meta_player
        eligible_positions = []
        for position in position_slots:
            if getattr(meta_player, position):
                eligible_positions.append(position)
        player_info = {
            'name': meta_player.name,
            'projection': player.projection,
            'salary': meta_player.salary,
            'positions': eligible_positions
        }
        meta_players[meta_player.name] = player_info
    
    # Create a linear programming problem
    model = LpProblem(name="Optimize_Lineups", sense=LpMaximize)

    # Separate each player into each position they are eligible for
    selected_players = {}
    position_lists = {
        'PG': [],
        'SG': [],
        'SF': [],
        'PF': [],
        'C': [],
        'G': [],
        'F': [],
        'UTIL': []
    }

    for name, meta_player_info in meta_players.items():
        for position in meta_player_info['positions']:
            position_lists[position].append(name)

    # Create binary variables for each player (1 if selected, 0 if not)
    selected_players = {}
    for position, position_list in position_lists.items():
        for player in position_list:
            position_specific_name = f"{player}_{position}"
            selected_players[position_specific_name] = LpVariable(name=position_specific_name, cat='Binary')

    # Objective function: maximize the total projection
    objective_terms = []
    for player_name, player_item in selected_players.items():
        meta_player_name = player_name.split('_')[0]
        objective_terms.append(meta_players[meta_player_name]['projection'] * player_item)
    model += lpSum(objective_terms)


    for position in position_lists:
        # Constraint: select exactly one player per position
        model += lpSum(selected_players[f"{player_name}_{position}"] for player_name in position_lists[position]) == 1

    # Constraint: limit the total salary to max_total_salary
    total_salary_constraint = lpSum(selected_players[player_name] * meta_players[player_name.split('_')[0]]['salary'] for player_name in selected_players) <= max_total_salary
    model += total_salary_constraint

    # Constraint: select exactly num_8 players
    model += lpSum(selected_players[player_name] for player_name in selected_players) == 8

    # Constraint: Select max one meta player:
    for player_name, player_item in meta_players.items():
        model += lpSum(selected_players[f"{player_name}_{position}"] for position in player_item['positions']) <= 1

    # Solve the problem
    model.solve()

    # Get the selected players
    selected_player_info = {key.split('_')[1]: key.split('_')[0] for key, value in selected_players.items() if value.value() == 1}
    return selected_player_info