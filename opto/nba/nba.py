from .models import Player
from pulp import LpMaximize, LpProblem, LpVariable, lpSum


def optimize_lineups(player_data, max_total_salary=50000):
    players = []
    position_slots = ['PG', 'SG', 'SF', 'PF', 'C', 'G', 'F', 'UTIL']
    for player in player_data:
        meta_player = player.meta_player
        players.append(
            {'name': meta_player.name, 'projection': player.projection, 'salary': meta_player.salary, 'F': meta_player.F, 'C': meta_player.C, 'G': meta_player.G, 'SG': meta_player.SG, 'PG': meta_player.PG, 'SF': meta_player.SF, 'PF': meta_player.PF})
    # Create the model

    # Create a linear programming problem
    model = LpProblem(name="Optimize_Lineups", sense=LpMaximize)

    # Create binary variables for each player (1 if selected, 0 if not)
    selected_players = LpVariable.dicts(
        "Selected", [player['name'] for player in players], cat='Binary')

    # Create binary variables for each position slot (1 if filled, 0 if not)
    position_vars = LpVariable.dicts("Position", position_slots, cat='Binary')

    # Objective function: maximize the total projection
    model += lpSum(player['projection'] *
                   selected_players[player['name']] for player in players)

    # Constraint: select exactly num_players players
    num_players = 8
    model += lpSum(selected_players[player['name']]
                   for player in players) == num_players

    # Constraint: limit the total salary to max_total_salary
    model += lpSum(player['salary'] * selected_players[player['name']]
                   for player in players) <= max_total_salary

   # Constraint: each player must be assigned to one position slot
    for player in players:
        model += lpSum(selected_players[player['name']] * position_vars[position] for position in position_slots) == 1

    # Constraint: each position slot must be filled
    for position in position_slots:
        model += lpSum(selected_players[player['name']]
                       for player in players if player[position.lower()] == 1) == position_vars[position]

    # Solve the problem
    model.solve()

    # Get the selected players and their positions
    selected_players_names = [player['name']
                              for player in players if selected_players[player['name']].value() == 1]
    selected_positions = {player['name']: [position for position in position_slots if position_vars[position].value() == 1][0]
                          for player in players if selected_players[player['name']].value() == 1}

    # Get the projections, salaries, and positions of the selected players
    selected_players_projections = [player['projection']
                                    for player in players if player['name'] in selected_players_names]
    selected_players_salaries = [
        player['salary'] for player in players if player['name'] in selected_players_names]
    selected_players_positions = [selected_positions[player['name']]
                                  for player in players if player['name'] in selected_players_names]

    print("Selected players:")
    for name, projection, salary, position in zip(selected_players_names, selected_players_projections, selected_players_salaries, selected_players_positions):
        print(
            f"{name} with projection: {projection}, salary: {salary}, position: {position}")

    return selected_players_names
