import oci
from prettytable import PrettyTable
import csv

def main():
    # ------------------------------------------------------------------
    # 1. CONFIG & INPUTS
    # ------------------------------------------------------------------
    # Load config from ~/.oci/config
    config = oci.config.from_file(profile_name="DEFAULT")
    
    # Ask for choice to use tenancy ID from config or provide manually
    use_config_tenancy_id = input("Do you want to use tenancy ID from config? (yes/no): ").strip().lower()
    if use_config_tenancy_id == 'yes':
        tenancy_id = config["tenancy"]
    else:
        tenancy_id = input("Enter your tenancy ID: ").strip()

    # Prompt user for region to check
    region_to_check = input("Enter region to check: ").strip()

    # --------------------------------------------------------------------
    # 2. FETCH SHAPES
    # --------------------------------------------------------------------
    shapes = []
    # We can paginate automatically by setting limit=None and using .list_call_get_all_results()
    # to ensure we get every shape in that region.
    response = oci.pagination.list_call_get_all_results(
        compute_client.list_shapes,
        compartment_id=compartment_id
    )
    shapes = response.data  # list of Shape objects

    # --------------------------------------------------------------------
    # 3. CREATE A PRETTY TABLE
    # --------------------------------------------------------------------
    table = PrettyTable(["Shape", "OCPUs", "Memory (GB)", "Processor Desc", "Is Flex?"])

    # Sort shapes by name, so the output is consistent
    shapes.sort(key=lambda s: s.shape)

    for s in shapes:
        # Some shapes might have None for OCPUs or memory_in_gbs
        ocpus = s.ocpus if s.ocpus is not None else "-"
        mem   = s.memory_in_gbs if s.memory_in_gbs is not None else "-"
        table.add_row([
            s.shape,
            ocpus,
            mem,
            s.processor_description if s.processor_description else "-",
            s.is_flexible
        ])

    # Print table to stdout
    print(table)

    # --------------------------------------------------------------------
    # 4. WRITE TO CSV FILE
    # --------------------------------------------------------------------
    csv_filename = "shapes.csv"
    with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        # Header row
        writer.writerow(["Shape", "OCPUs", "Memory (GB)", "Processor Desc", "Is Flexible"])

        for s in shapes:
            ocpus = s.ocpus if s.ocpus is not None else "-"
            mem   = s.memory_in_gbs if s.memory_in_gbs is not None else "-"
            writer.writerow([
                s.shape,
                ocpus,
                mem,
                s.processor_description if s.processor_description else "-",
                s.is_flexible
            ])

    print(f"\nWrote table to {csv_filename} as well.")

if __name__ == "__main__":
    main()
