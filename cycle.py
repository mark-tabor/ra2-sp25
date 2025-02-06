import pandas as pd
import networkx as nx

"""
6.180 Appeals Fix
Author: jorgem13

Workflow to be done every 1-2 days to accumulate responses:
    (1) Download R+T Appeals Google Form responses as a CSV file and write it to ./appeals.csv
        (1.1) [Recommended] For form validation, download R+T Assignments Google Sheet and 
              write it to ./current_assignments.csv
    (2) Run `cycle.py` (this file).
        (2.1) If you get cycles, run this file several times as cycle detection is nondeterministic;
              find cycles that fix as many schedule conflicts as possible.
        (2.2) If you don't get cycles, go to line 383 and change the arguments to `shift_path` according
              to its spec. Fix the path.
                (2.2.1) Note that this path only focuses on balancing either the rec or the tut,
                        so verify the other section works before applying.
        (2.3) If you got nothing, either you're done or you have to put in some manual work. Rip.
    (3) Assign students according to the new fixes found in (2).
"""

# Including these strings cause I'm too lazy to copy paste
N = "Name"
K = "Kerb (without @mit.edu)"
T = "Timestamp"
R = "Reason for Switching (if your case doesn't fit into these options, email 6.1800-utas@mit.edu with your specific case)"
S = "Status"
TP = "Team preference"
SC = "Schedule conflict"
CR = "Which recitation section are you currently in?"
CT = "Which tutorial section are you currently in?"
DRT = "Times that you are available for recitation"
DTT = "Times that you are available for tutorial (leave blank if you are currently ok)"
DRS = "Which recitation sections would you like?"
DTS = "Which tutorial section would you like?"

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
        In the case of an invalid input, should probably raise it and explain why its invalid and where
    """
    as_df = pd.read_csv(assignments_path)

    # (1)

    # (2)

    return


def data_process(appeals_path, assignments_path=None):
    """
    Similar to ./data_process.py. Returns pandas dataframe and a set of names of students who have schedule conflicts.
    Includes validation if `assignments_path` is included.
    """

    df = pd.read_csv(appeals_path)
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=[K, T])
    
    # Fix extra @
    df[K] = df[K].str.replace('@mit.edu', '', regex=False)

    # Fix spacing between time range and meridiem. Should probably change the form to remove this code later
    df[CR] = df[CR].str.replace(' pm', 'pm', regex=False)
    df[CR] = df[CR].str.replace(' am', 'am', regex=False)
    df[CT] = df[CT].str.replace(' pm', 'pm', regex=False)
    df[CT] = df[CT].str.replace(' am', 'am', regex=False)
    df[DRT] = df[DRT].str.replace(' pm', 'pm', regex=False)
    df[DRT] = df[DRT].str.replace(' am', 'am', regex=False)
    df[DTT] = df[DTT].str.replace(' pm', 'pm', regex=False)
    df[DTT] = df[DTT].str.replace(' am', 'am', regex=False)
    df[DRS] = df[DRS].str.replace(' pm', 'pm', regex=False)
    df[DRS] = df[DRS].str.replace(' am', 'am', regex=False)
    df[DTS] = df[DTS].str.replace(' pm', 'pm', regex=False)
    df[DTS] = df[DTS].str.replace(' am', 'am', regex=False)
    
    # Get most recent submission
    df[T] = pd.to_datetime(df[T], errors="coerce")
    df = df.dropna(subset=[T])
    df_filtered = df.loc[df.groupby(K)[T].idxmax()]

    # Discard appeals that were attended to
    df_filtered = df_filtered[df_filtered[S].isna() | (df_filtered[S].str.strip() == "")]

    # Keep names of students who have schedule conflicts, as they have higher priority
    sc_students = set()
    for _, row in df_filtered.iterrows():
        if row[R].strip() == SC:
            sc_students.add(row[N].strip())

    if assignments_path is not None:
        validate_appeals(df_filtered, assignments_path)
    
    return df_filtered, sc_students


def generate_desired_sections(row):
    """
    Generates a list of valid desired sections the student in this row of the dataframe 
    wants to go to. 
    
    If their appeal is for a schedule conflict, it returns a list of sections
    of the form [(Recitation Section, Tutorial Section), ...]

    If their appeal is for a team preference, it returns a list of times
    of the form [(Recitation Time, Tutorial Time), ...]
    """
    reason = row[R].strip()
    # Where they want to go
    if reason == TP:
        desired_recitation_sections = str(row[DRS]).split(", ")
        desired_tutorial_sections = str(row[DTS]).split(", ")
    elif reason == SC:
        desired_recitation_sections = str(row[DRT]).split(", ")
        desired_tutorial_sections = str(row[DTT]).split(", ")

    # Generate desired sections
    desired_sections = []
    for drs in desired_recitation_sections:
        for dts in desired_tutorial_sections:
            if reason == TP:
                desired_instructors = (drs.split(" with ")[1].strip(), dts.split(" with ")[1].strip())
                if desired_instructors in valid_rec_tut_pairs:
                    desired_sections.append((drs.strip(), dts.strip()))
            elif reason == SC:
                desired_sections.append((drs.strip(), dts.strip()))
    return desired_sections

def df_to_graph(df):
    """
    Converts pandas dataframe to a graph G = (V, E) using NetworkX where 
    v ∈ V is a pair (Student, Section), where Section is a pair (Recitation Section, Tutorial Section)
    e ∈ E is  a pair (u, v) where u, v ∈ V describes the relationship u_name desires v_section
    """

    G = nx.DiGraph()

    # Store sections up for grabs and the students in them
    section_to_students = {}
    for _, row in df.iterrows():
        student = row[N].strip()
        current_section = (
            row[CR].strip(), 
            row[CT].strip()
        )
        section_to_students.setdefault(current_section, []).append(student.strip())

    # Add edges to others currently in desired sections
    for _, row in df.iterrows():

        # Student info
        student = row[N].strip()
        reason = row[R].strip()
        current_section = (row[CR].strip(), row[CT].strip())
        if reason != TP and reason != SC:
            raise Exception("Invalid reason in df_to_graph")
        desired_sections = generate_desired_sections(row)
        # Match the student to sections they can move to
        if reason == TP:
            for ds in desired_sections:
                if ds in section_to_students:
                    for target_student in section_to_students[ds]:
                        G.add_edge((student, current_section), (target_student, ds))
        elif reason == SC:
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
    Note: `nx.simple_cycles` is nondeterministic, so run this puppy a couple times.
    """
    cycles = []
    i=0
    for cycle in nx.simple_cycles(G):
        if i >= 1000: # Max branching factor of tree. I'm sure you can guess the tradeoffs
            break
        cycles.append(cycle)
        i+=1
    return sorted([list(cycle) for cycle in cycles], key=len, reverse=True)

def optimal_removal(G, sc_students=None):
    """
    Iteratively remove cycles and see which selection of cycles results in the most students being satisfied.

    Include `sc_students`, a set of names of students who have schedule conflicts, to prioritize satisfying schedule conflicts 
    over general appeals.

    If `sc_students` not included, returns number of satisfied appeals. Otherwise, returns number of satisfied schedule conflicts.
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
        print(f"\nBest free cycles ({fix_rate}% of appeals fixed ; {sc_fix_rate}% of schedule conflicts fixed):")
        for i, cycle in enumerate(reversed(cycles)):
            names = [name for name, _ in cycle]
            print(f"\t{i+1}. {" -> ".join(names)}")
        return True
    else:
        print("No easy cycles found. Rip.\n")
        return False

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
    G_c = G.copy()
    G_c.remove_nodes_from([node for node in list(G_c.nodes) if node[0] in sc_students_fixed])

    # Second, with what's left of `G`, try to further squeeze out appeals in general
    cycles, extra = optimal_removal(G_c)
    appeals_fixed = num_students_fixed + extra
    fix_rate = round(appeals_fixed/num_students*100, 2)
    for cycle in cycles:
        sc_students_fixed |= set(node[0] for node in cycle) & sc_students
    sc_fixed = len(sc_students_fixed)
    sc_fix_rate = round(sc_fixed/len(sc_students)*100, 2)

    # Third, combine cycles found in both stages
    final_chain = sc_cycles + cycles

    if final_chain:
        print(f"Best cycles for schedule conflicts ({sc_fix_rate}% of schedule conflicts fixed ; {fix_rate}% of appeals fixed):")
        for i, cycle in enumerate(reversed(final_chain)):
            names = [name for name, _ in cycle]
            print(f"\t{i+1}. {" -> ".join(names)}")
        return True
    else:
        print("No easy cycles found for schedule conflicts. Rip.\n")
        return False

def shift_path(G, df, sc_students, sections_u, sections_v, tutorial=True):
    """
    If no cycles are found, we can try to move students around, preferably from bigger rosters to lower rosters.
    u, v ∈ V as described in `df_to_graph`. Sections in`sections_u` will lose one student, and those in `sections_v` will gain one student.

    Ensure that the corresponding section does not get unbalanced. For example, a path might balance a pair of tutorials,
    but it could also make the corresponding pair of recitations worse

    We prioritize tutorials, so we assume that is what is to balance, if balanceding recitation, set `tutorial` to False

    Example call:
    path(
        G, 
        df, 
        {"Jorge Martinez", "Mark Tabor", "Rachel Loh", "David Choi"}, 
        ["TR 12-1pm with Lili Wilson"], 
        ["TR 2-3pm with Katrina LaCurts"], 
        False
    )

    TODO Future work : Include stats sheet to balance optimally
    """

    found_some = False
    for section_u in sections_u:
        for section_v in sections_v:
            i = 1 if tutorial else 0
            source = "source_string"
            sink = "sink_string"

            for _, row in df.iterrows():
                name = row[N]
                reason = row[R].strip()
                current_section = (row[CR], row[CT])

                if current_section[i] == section_u:
                    G.add_edge(source, (name, current_section))

                desired_sections = generate_desired_sections(row)
                
                # Match the student to sections they can move to
                if reason == TP:
                    for ds in desired_sections:
                        if ds[i] == section_v:
                            G.add_edge((name, current_section), sink)
                elif reason == SC:
                    for dt in desired_sections:
                        section_v_time = section_v.split(" with ")[0]
                        if dt[i] == section_v_time:
                            G.add_edge((name, current_section), sink)

            nodes = set(G.nodes())
            if source not in nodes or sink not in nodes:
                print(f"No free paths from {section_u} to {section_v}. Gotta make some tough calls.")
                return

            paths = list(nx.all_simple_paths(G, source, sink))

            if paths:
                found_some = True
                print(f"\nRemoving from {section_u} and adding to {section_v}")
                print("Potential paths (ranked by number of appeals met):")
                for i, path in enumerate(sorted(paths, key=len, reverse=True)):
                    print(f"\t{i+1}. " + " -> ".join(node[0] for node in path if node != source and node != sink))
                print("Potential paths (ranked by number of schedule conflicts fixed):")
                for i, path in enumerate(sorted(paths, key=lambda path: sum(1 for node in path if node[0] in sc_students), reverse=True)):
                    print(f"\t{i+1}. " + " -> ".join(node[0] for node in path if node != source and node != sink))
            else:
                print(f"No free paths from {section_u} to {section_v}")
    if not found_some:
        print(f"No free paths. Gotta make some tough calls.")
    


def main():
    # Inputs
    appeal_path = "./appeals.csv"

    # TODO current_assignment_path = "./current_assignments.csv"

    # Process inputs 
    df, sc_students = data_process(appeal_path)
    num_students = df.shape[0]

    # Generate graph
    G = df_to_graph(df)

    # Find cycles
    success = appeals_report(G, sc_students, num_students)
    success = sc_report(G, sc_students, num_students) or success

    # Find path from section A to section B
    sections_u = [
        "TR 11am-12pm with Hari Balakrishnan",
        "TR 1-2pm with Katrina LaCurts",
    ]
    sections_v = [
        "TR 10-11am with Hari Balakrishnan",
        "TR 2-3pm with Katrina LaCurts",
    ]
    shift_path(G, df, sc_students, sections_u, sections_v, False)

    print("\nRemember to manually fix schedule conflicts and confirm special cases/exceptions!\n")

if __name__ == "__main__":
    main() 
