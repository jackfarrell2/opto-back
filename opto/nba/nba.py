from pulp import LpMaximize, LpProblem, LpVariable, lpSum

def optimize_lineups(player_data, num_players=8, max_total_salary=50000):
    players = []
    for player in player_data:
        meta_player = player.meta_player
        players.append({'name': meta_player.name, 'projection': player.projection, 'salary': meta_player.salary})
    
    # Create a linear programming problem
    model = LpProblem(name="Optimize_Lineups", sense=LpMaximize)

    # Create binary variables for each player (1 if selected, 0 if not)
    selected_players = LpVariable.dicts("Selected", [player['name'] for player in players], cat='Binary')

    # Objective function: maximize the total projection
    model += lpSum(player['projection'] * selected_players[player['name']] for player in players)

    # Constraint: select exactly num_players players
    model += lpSum(selected_players[player['name']] for player in players) == num_players

    # Constraint: limit the total salary to max_total_salary
    model += lpSum(player['salary'] * selected_players[player['name']] for player in players) <= max_total_salary

    # Constraint: 

    # Solve the problem
    model.solve()

    # Get the selected players
    selected_players_names = [player['name'] for player in players if selected_players[player['name']].value() == 1]

    # Get the projections and salaries of the selected players
    selected_players_projections = [player['projection'] for player in players if player['name'] in selected_players_names]
    selected_players_salaries = [player['salary'] for player in players if player['name'] in selected_players_names]

    print("Selected players:")
    for name, projection, salary in zip(selected_players_names, selected_players_projections, selected_players_salaries):
        print(f"{name} with projection: {projection} and salary: {salary}")

    return selected_players_names
