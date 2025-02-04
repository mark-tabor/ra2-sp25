import pandas as pd
import networkx as nx

def data_process(file_path):
    """
    Similar to ./data_process.py
    """
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    
    df = df.dropna(subset=["Kerb (without @mit.edu)", "Timestamp"])
    
    df['Kerb (without @mit.edu)'] = df['Kerb (without @mit.edu)'].str.replace('@mit.edu', '', regex=False)
    
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df = df.dropna(subset=["Timestamp"])
    df_filtered = df.loc[df.groupby("Kerb (without @mit.edu)")["Timestamp"].idxmax()]


    sc_students = set()
    for _, row in df_filtered.iterrows():
        if row["Reason for Switching (if your case doesn't fit into these options, email 6.1800-utas@mit.edu with your specific case)"].strip() == "Schedule conflict":
            sc_students.add(row["Name"].strip())
    
    return df_filtered, sc_students


def df_to_graph(df):
    """
    Converts pandas dataframe to NetworkX graph. Nodes will be of the form (Student, Current Section), 
    where the current section will be a pair of the recitation and tutorial section.
    Directed edges will go from it to all other nodes that have current sections that the student desires.
    """

    G = nx.DiGraph()

    # Store sections up for grabs
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

        student = row["Name"].strip()
        current_section = (
            row["Which recitation section are you currently in?"].strip(), 
            row["Which tutorial section are you currently in?"].strip()
        )

        desired_recitation_sections = str(row["Which recitation sections would you like?"]).split(", ")
        desired_tutorial_sections = str(row["Which tutorial section would you like?"]).split(", ")

        # `desired_sections` includes sections with incompatible rec+tut instructors, but 
        # `section_to_students` only has valid sections, so this shouldn't be an issue
        desired_sections = []
        for drs in desired_recitation_sections:
            for dts in desired_tutorial_sections:
                desired_sections.append((drs.strip(), dts.strip()))

        for ds in desired_sections:
            if ds in section_to_students:
                for target_student in section_to_students[ds]:
                    G.add_edge((student, current_section), (target_student, ds))

    return G

def find_cycles(G):
    """
    List out potential cycles of students we can switch. Tackle bigger cycles to satisfy more students.
    """
    cycles = list(nx.simple_cycles(G))
    return sorted([list(cycle) for cycle in cycles], key=len, reverse=True)

def optimal_removal(G, sc_students=None):
    """
    Iteratively remove cycles and see which selection of cycles results in the most students being satisfied
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
        satisfied = len(cycle) if sc_students is None else len((set(cycle) & sc_students))
        if satisfied + count > max_count:
            max_cycle_groups = cycle_groups + [cycle]
            max_count = satisfied + count
    return max_cycle_groups, max_count

def main():
    file_path = "./form_data.csv"
    df, sc_students = data_process(file_path)
    num_students = df.shape[0]
    num_sc_students = len(sc_students)
    G = df_to_graph(df)

    # Overall
    swap_chains, count = optimal_removal(G)
    overall_fix = round(count/num_students*100, 2)
    sc_students_fixed = set()
    for chain in swap_chains:
        sc_students_fixed |= (sc_students & set(chain))
    sc_students_fixed = len(sc_students_fixed)
    sc_students_fixed = round(sc_students_fixed/num_sc_students*100, 2)

    if swap_chains:
        print(f"\nBest free swaps ({overall_fix}% of appeals fixed ; {sc_students_fixed}% of schedule conflicts fixed):")
        for i, swap_chain in enumerate(reversed(swap_chains)):
            names = [name for name, _ in swap_chain]
            print(f"\t{i+1}. {" -> ".join(names)}")
    else:
        print("No easy swaps found in general. Rip.\n")

    # Schedule conflicts
    sc_swap_chains, sc_count = optimal_removal(G, sc_students)
    sc_names = set()
    for chain in sc_swap_chains:
        sc_names |= set(chain)
    removed_nodes = [node for node in list(G.nodes) if node[0] in sc_names]
    G.remove_nodes_from(removed_nodes)
    swap_chains, extra = optimal_removal(G)
    overall_count = sc_count + extra
    overall_fix = round(overall_count/num_students*100, 2)
    sc_fix = round(sc_count/num_sc_students*100, 2)
    final_chain = sc_swap_chains + swap_chains

    print("\n")
    if final_chain:
        print(f"Best swaps for schedule conflicts ({sc_fix}% of schedule conflicts fixed ; {overall_fix}% of appeals fixed):")
        for i, sc_swap_chain in enumerate(reversed(final_chain)):
            names = [name for name, _ in sc_swap_chain]
            print(f"\t{i+1}. {" -> ".join(names)}")
    else:
        print("No easy swaps found for schedule conflicts. Rip.\n")
    
    print("\nRemember to manually fix schedule conflicts and confirm special cases/exceptions!\n")

if __name__ == "__main__":
    main() 
