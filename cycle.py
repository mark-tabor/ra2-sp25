import pandas as pd
import networkx as nx

valid_rec_tut_pairs = {
    ("Hari Balakrishnan", "Liz Stevens"),
    ("Olivia Brode-Roger", "Rebecca Thorndike-Breeze"),
    ("Olivia Brode-Roger", "Rachel Molko"),
    ("Mark Day", "Katie Bruner,"),
    ("Mark Day", "Nicole Cunningham-Frisbey"),
    ("Katrina LaCurts", "Jessie Stickgold-Sarah"),
    ("Larry Rudolph", "Kate Parsons"),
    ("Larry Rudolph", "Kristen Starkowski"),
    ("Karen Sollins", "Michael Trice"),
    ("Lili Wilson", "Sarah Bates"),
}

def validate_appeals(ap_df, assignments_path):
    """
    TODO We need to validate the appeals. Possible cases to check for:
        (1) Requests for incompatible recitation + instructor 
        (2) Stating they are currently in section A when they are really in section B
        (*) [Add more as they come in]
    """
    as_df = pd.read_csv(assignments_path)

    # (1)

    # (2)

    return


def data_process(appeals_path, assignments_path=None):
    """
    Similar to ./data_process.py. Returns pandas dataframe and a set of names of students who have schedule conflicts.
    Includes validation if assignments_path is included.
    """

    df = pd.read_csv(appeals_path)
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=["Kerb (without @mit.edu)", "Timestamp"])
    
    # Fix extra @
    df['Kerb (without @mit.edu)'] = df['Kerb (without @mit.edu)'].str.replace('@mit.edu', '', regex=False)
    
    # Get most recent submission
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.dropna(subset=["Timestamp"])
    df_filtered = df.loc[df.groupby("Kerb (without @mit.edu)")["Timestamp"].idxmax()]

    # Discard appeals that were attended to
    df_filtered = df_filtered[df_filtered["Status"].isna() | (df_filtered["Status"].str.strip() == "")]

    # Keep names of students who have schedule conflicts, as they have higher priority
    sc_students = set()
    for _, row in df_filtered.iterrows():
        if row["Reason for Switching (if your case doesn't fit into these options, email 6.1800-utas@mit.edu with your specific case)"].strip() == "Schedule conflict":
            sc_students.add(row["Name"].strip())

    if assignments_path is not None:
        validate_appeals(df_filtered, assignments_path)
    
    return df_filtered, sc_students


def df_to_graph(df):
    """
    Converts pandas dataframe to a graph G = (V, E) using NetworkX where...
    v ∈ V is a pair (Student, Section), where Section is a pair (Recitation Section, Tutorial Section)
    e ∈ E is  a pair (u, v) where u, v ∈ V describes the relationship u_name desires v_section
    """

    G = nx.DiGraph()

    # Store sections up for grabs and the students in them
    section_to_students = {}
    for _, row in df.iterrows():
        student = row["Name"].strip()
        current_section = (
            row["Which recitation section are you currently in?"].strip(), 
            row["Which tutorial section are you currently in?"].strip()
        )
        section_to_students.setdefault(current_section, []).append(student.strip())

    # Add edges to others currently in desired sections
    for _, row in df.iterrows():

        # Student info
        student = row["Name"].strip()
        reason = row["Reason for Switching (if your case doesn't fit into these options, email 6.1800-utas@mit.edu with your specific case)"].strip()
        if reason != "Team preference" and reason != "Schedule conflict":
            raise Exception("Invalid reason in df_to_graph")
        current_section = (
            row["Which recitation section are you currently in?"].strip(), 
            row["Which tutorial section are you currently in?"].strip()
        )

        # Where they want to go
        if reason == "Team preference":
            desired_recitation_sections = str(row["Which recitation sections would you like?"]).split(", ")
            desired_tutorial_sections = str(row["Which tutorial section would you like?"]).split(", ")
        elif reason == "Schedule conflict":
            desired_recitation_sections = str(row["Times that you are available for recitation"]).split(", ")
            desired_tutorial_sections = str(row["Times that you are available for tutorial (leave blank if you are currently ok)"]).split(", ")

        # Generate desired sections
        desired_sections = []
        for drs in desired_recitation_sections:
            for dts in desired_tutorial_sections:
                if reason == "Team preference":
                    desired_instructors = (drs.split(" with ")[1].strip(), dts.split(" with ")[1].strip())
                    if desired_instructors in valid_rec_tut_pairs:
                        desired_sections.append((drs.strip(), dts.strip()))
                elif reason == "Schedule conflict":
                    desired_sections.append((drs.strip(), dts.strip()))

        # Match the student to sections they can move to
        if reason == "Team preference":
            for ds in desired_sections:
                if ds in section_to_students:
                    for target_student in section_to_students[ds]:
                        G.add_edge((student, current_section), (target_student, ds))
        elif reason == "Schedule conflict":
            for dt in desired_sections:
                for ds, target_students in section_to_students.items():
                    t = tuple(s.split(" with ")[0] for s in ds)
                    if t == dt:
                        for target_student in target_students:
                            G.add_edge((student, current_section), (target_student, ds))

    return G

def find_cycles(G):
    """
    List out potential cycles of students we can switch. Tackle bigger cycles to satisfy more students.
    Note: nx.simple_cycles is nondeterministic.
    """
    cycles = []
    i=0
    for cycle in nx.simple_cycles(G):
        if i >=1000: # Max branching factor of tree. I'm sure you can guess the tradeoffs
            break
        cycles.append(cycle)
        i+=1
    return sorted([list(cycle) for cycle in cycles], key=len, reverse=True)

def optimal_removal(G, sc_students=None):
    """
    Iteratively remove cycles and see which selection of cycles results in the most students being satisfied.

    Include sc_students, a set of names of students who have schedule conflicts, to prioritize satisfying schedule conflicts 
    over general appeals.

    If sc_students not included, returns number of satisfied appeals. Otherwise, returns number of satisfied schedule conflicts.
    """
    cycles = find_cycles(G)
    if not cycles:
        return [], 0

    max_cycle_groups = []
    max_count = 0
    for cycle in cycles:
        G_c = G.copy()
        for node in cycle:
            G_c.remove_node(node)
        cycle_groups, count = optimal_removal(G_c, sc_students)
        satisfied = len(cycle) if sc_students is None else len(set(node[0] for node in cycle) & sc_students)
        if satisfied + count > max_count:
            max_cycle_groups = cycle_groups + [cycle]
            max_count = satisfied + count
    return max_cycle_groups, max_count

def appeals_report(G, sc_students, num_students):
    """
    Workflow to maximize appeals fixed.
    """
    cycles, appeals_fixed = optimal_removal(G)
    fix_rate = round(appeals_fixed/num_students*100, 2)
    sc_students_fixed = set()
    for cycle in cycles:
        sc_students_fixed |= sc_students & set(node[0] for node in cycle)
    sc_fixed = len(sc_students_fixed)
    sc_fix_rate = round(sc_fixed/len(sc_students)*100, 2)
    if cycles:
        print(f"\nBest free swaps ({fix_rate}% of appeals fixed ; {sc_fix_rate}% of schedule conflicts fixed):")
        for i, cycle in enumerate(reversed(cycles)):
            names = [name for name, _ in cycle]
            print(f"\t{i+1}. {" -> ".join(names)}")
    else:
        print("No easy swaps found in general. Rip.\n")


def sc_report(G, sc_students, num_students):
    """
    Workflow to maximize resolved schedule conflicts.
    """
    # First, focus on maximizing schedule conflicts
    sc_cycles, sc_fixed = optimal_removal(G, sc_students)
    sc_students_fixed = set()
    num_students_fixed = 0
    for cycle in sc_cycles:
        sc_students_fixed |= set(node[0] for node in cycle) & sc_students
        num_students_fixed += len(cycle)

    # Now that they are satisfied, we can remove these nodes from our graph
    G.remove_nodes_from([node for node in list(G.nodes) if node[0] in sc_students_fixed])

    # Second, what's left of G, try to further squeze out appeals in general
    cycles, extra = optimal_removal(G)
    appeals_fixed = num_students_fixed + extra
    fix_rate = round(appeals_fixed/num_students*100, 2)
    for cycle in cycles:
        sc_students_fixed |= set(node[0] for node in cycle) & sc_students
    sc_fixed = len(sc_students_fixed)
    sc_fix_rate = round(sc_fixed/len(sc_students)*100, 2)

    # Third, combine cycles found in both stages
    final_chain = sc_cycles + cycles

    print("\n")
    if final_chain:
        print(f"Best swaps for schedule conflicts ({sc_fix_rate}% of schedule conflicts fixed ; {fix_rate}% of appeals fixed):")
        for i, cycle in enumerate(reversed(final_chain)):
            names = [name for name, _ in cycle]
            print(f"\t{i+1}. {" -> ".join(names)}")
    else:
        print("No easy swaps found for schedule conflicts. Rip.\n")
    
    print("\nRemember to manually fix schedule conflicts and confirm special cases/exceptions!\n")


def main():
    # Inputs
    appeal_path = "./appeals.csv"
    current_assignment_path = "./current_assignments.csv"

    # Process inputs 
    df, sc_students = data_process(appeal_path, current_assignment_path)
    num_students = df.shape[0]

    # Generate graph
    G = df_to_graph(df)

    # Find cycles
    appeals_report(G, sc_students, num_students)
    sc_report(G, sc_students, num_students)

if __name__ == "__main__":
    main() 
