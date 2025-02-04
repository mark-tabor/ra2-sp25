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
    
    return df_filtered


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
        current_section = (row["Which recitation section are you currently in?"].strip(), row["Which tutorial section are you currently in?"].strip())
        section_to_students.setdefault(current_section, []).append(student.strip())

    # Add edges to others currently in desired sections
    for _, row in df.iterrows():

        student = row["Name"].strip()
        current_section = (row["Which recitation section are you currently in?"].strip(), row["Which tutorial section are you currently in?"].strip())

        desired_recitation_sections = str(row["Which recitation sections would you like?"]).split(", ")
        desired_tutorial_sections = str(row["Which tutorial section would you like?"]).split(", ")

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

def optimal_removal(G):
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
        cycle_groups, count = optimal_removal(G_c)
        if len(cycle) + count > max_count:
            max_cycle_groups = cycle_groups + [cycle]
            max_count = len(cycle) + count
    return max_cycle_groups, max_count

def main():
    file_path = "./form_data.csv"
    df = data_process(file_path)
    num_students = df.shape[0]
    G = df_to_graph(df)
    swap_chains, count = optimal_removal(G)

    if swap_chains:
        print(f"Best free swaps ({round(count/num_students*100, 2)}% fix rate):")
        for i, swap_chain in enumerate(reversed(swap_chains)):
            names = [name for name, _ in swap_chain]
            print(f"{i+1}. {" -> ".join(names)}")
        print("Remember to manually fix schedule conflicts and confirm special cases/exceptions.")
    else:
        print("No easy swaps found. Rip.")

if __name__ == "__main__":
    main() 
