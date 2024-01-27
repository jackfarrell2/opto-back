from .models import Player
from pulp import LpMaximize, LpProblem, LpVariable, lpSum


def optimize_lineups(player_data, max_total_salary=50000):
    players = []
    position_slots = ['PG', 'SG', 'SF', 'PF', 'C', 'G', 'F', 'UTIL']
    for player in player_data:
        meta_player = player.meta_player
        players_eligible_positions = {'PG': False, 'SG': False, 'SF': False, 'PF': False, 'C': False, 'G': False, 'F': False, 'UTIL': False}
        for position in position_slots:
            if getattr(meta_player, position):
                players_eligible_positions[position] = True
        players_positions_list = []
        for k, v in players_eligible_positions.items():
            if v:
                players_positions_list.append(k)
        players.append(
            {'name': meta_player.name, 'projection': player.projection, 'salary': meta_player.salary, 'positions': players_positions_list})
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


    # Solve the problem
    model.solve()


    if LpProblem.status[model] == 1:  # 1 means the problem has been solved
        print("Optimal lineup:")
        for player in players:
            if selected_players[player['name']].varValue == 1:
                print(f"{player['name']} - {', '.join(player['positions'])}")

        # Print the total projection of the optimal lineup
        total_projection = lpSum(player['projection'] * selected_players[player['name']] for player in players).value()
        print(f"\nTotal Projection: {total_projection}")

        # Print the total salary of the optimal lineup
        total_salary = lpSum(player['salary'] * selected_players[player['name']] for player in players).value()
        print(f"Total Salary: {total_salary}")
        return('Hi')

    else:
        print("The problem could not be solved.")
        return('Hi')