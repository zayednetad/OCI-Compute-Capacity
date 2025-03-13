import oci
import json
import datetime

def main(output_json=False):
    """
    If output_json=True, the script will generate a JSON file of results.
    Otherwise, it only prints to terminal.
    """

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

    # Prompt user for shapes to check
    shapes_input = input("Enter shapes to check (space-separated, e.g., 'VM.Standard.E5.Flex VM.Standard3.Flex'): ").strip()
    shapes_to_check = [{"shape": shape, "ocpus": None, "memory_in_gbs": None} for shape in shapes_input.split()]

    # Fault Domains are typically 1, 2, 3 in each AD
    fault_domains = ["FAULT-DOMAIN-1", "FAULT-DOMAIN-2", "FAULT-DOMAIN-3"]

    # This list will collect all results if we choose to dump as JSON
    results = []

    # ------------------------------------------------------------------
    # 2. PROCESS THE REGION
    # ------------------------------------------------------------------
    print(f"\n=== REGION: {region_to_check} ===")
    config["region"] = region_to_check

    # IdentityClient for listing ADs
    identity_client = oci.identity.IdentityClient(config)
    ads_response = identity_client.list_availability_domains(compartment_id=tenancy_id)

    # Convert returned AD objects into a set of unique AD names
    unique_ad_names = {ad_obj.name for ad_obj in ads_response.data}

    # ComputeClient for capacity reports
    compute_client = oci.core.ComputeClient(config)

    # ------------------------------------------------------------------
    # 3. LOOP OVER UNIQUE AD NAMES
    # ------------------------------------------------------------------
    for ad_name in sorted(unique_ad_names):
        print(f"  -> Availability Domain: {ad_name}")

        # ------------------------------------------------------------------
        # 4. LOOP OVER SHAPES & FAULT DOMAINS
        # ------------------------------------------------------------------
        for shape_info in shapes_to_check:
            shape_name = shape_info["shape"]
            desired_ocpus = shape_info["ocpus"]
            desired_memory = shape_info["memory_in_gbs"]

            print(f"     - Shape: {shape_name}")

            for fd in fault_domains:
                # Build one shape availability detail
                shape_avail = oci.core.models.CreateCapacityReportShapeAvailabilityDetails(
                    fault_domain=fd,
                    instance_shape=shape_name
                )

                # If it's a Flex shape, add instanceShapeConfig
                if desired_ocpus is not None and desired_memory is not None:
                    shape_avail.instance_shape_config = {
                        "ocpus": desired_ocpus,
                        "memoryInGBs": desired_memory
                    }

                # You can pass multiple shapes in one request, but let's do one shape at a time
                request_details = oci.core.models.CreateComputeCapacityReportDetails(
                    compartment_id=tenancy_id,
                    availability_domain=ad_name,
                    shape_availabilities=[shape_avail]
                )

                # ------------------------------------------------------------------
                # 5. CALL THE CAPACITY REPORT ENDPOINT
                # ------------------------------------------------------------------
                try:
                    response = compute_client.create_compute_capacity_report(
                        create_compute_capacity_report_details=request_details
                    )

                    # The "data" property is a ComputeCapacityReport object
                    report = response.data

                    # Each shape in shape_availabilities is returned in report.shape_availabilities
                    for shape_availability in report.shape_availabilities:
                        # e.g. "AVAILABLE", "NO_CAPACITY", "RESERVED", etc.
                        status = shape_availability.availability_status  
                        # Count of how many instances can be launched
                        count = shape_availability.available_count         
                        # The shape requested
                        shape_used = shape_availability.instance_shape
                        # The fault domain
                        fd_used = shape_availability.fault_domain

                        # If flex, this config shows how many OCPUs/memory were actually accounted for
                        shape_config = shape_availability.instance_shape_config
                        if shape_config:
                            ocpus_used = shape_config.ocpus
                            mem_used = shape_config.memory_in_gbs
                            config_str = f"(OCPUs={ocpus_used}, Mem={mem_used}GB)"
                        else:
                            config_str = ""

                        # Print to terminal
                        print(
                            f"       - Fault Domain: {fd_used} -> Status: {status}, Count: {count}"
                        )

                        # If output_json is True, save details to our results list
                        if output_json:
                            results.append({
                                "region": region_to_check,
                                "availability_domain": ad_name,
                                "fault_domain": fd_used,
                                "shape": shape_used,
                                "requested_ocpus": desired_ocpus,
                                "requested_memory_gbs": desired_memory,
                                "actual_ocpus": ocpus_used if shape_config else None,
                                "actual_memory_gbs": mem_used if shape_config else None,
                                "status": status,
                                "count": count
                            })

                except oci.exceptions.ServiceError as e:
                    print(
                        f"       [ERROR] Region: {region_to_check}, AD: {ad_name}, FD: {fd}, "
                        f"Shape: {shape_name}: {e.code} - {e.message}"
                    )

    print("--- End of Region ---")

    # ------------------------------------------------------------------
    # 6. OUTPUT JSON IF REQUESTED
    # ------------------------------------------------------------------
    if output_json:
        # Timestamped file name
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capacity_report_{timestamp_str}.json"

        # Write the collected results
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        print(f"\nJSON file generated: {filename}")


if __name__ == "__main__":
    # You can toggle this flag:
    main(output_json=True)
    # Or call main(False) if you don’t want a JSON file
