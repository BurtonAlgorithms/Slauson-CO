#!/usr/bin/env python3
"""
Check Canva Design Import Job Status
Usage: python check_canva_import_status.py <job_id>
"""

import sys
from canva_integration import CanvaIntegration

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_canva_import_status.py <job_id>")
        print("\nExample:")
        print("  python check_canva_import_status.py e541dbc8-5025-4cd2-9ff5-1e7cba289991")
        sys.exit(1)
    
    job_id = sys.argv[1]
    
    print(f"Checking Canva import job status for: {job_id}\n")
    
    try:
        canva = CanvaIntegration()
        
        # Check status once
        status = canva.check_import_job_status(job_id)
        
        print(f"Status: {status['status']}")
        print(f"Job ID: {status['job_id']}")
        
        if status['status'] == 'success':
            print(f"\n✅ Import completed successfully!")
            if 'design_id' in status:
                print(f"Design ID: {status['design_id']}")
            if 'design_url' in status:
                print(f"Design URL: {status['design_url']}")
        elif status['status'] == 'failed':
            print(f"\n❌ Import failed!")
            if 'error' in status:
                print(f"Error: {status['error']}")
        elif status['status'] == 'in_progress':
            print(f"\n⏳ Import is still in progress...")
            print(f"\nTo poll until completion, use:")
            print(f"  python check_canva_import_status.py {job_id} --wait")
        
        # If --wait flag is provided, poll until completion
        if len(sys.argv) > 2 and sys.argv[2] == '--wait':
            print(f"\nPolling until completion (max 60 seconds)...")
            final_status = canva.wait_for_import_completion(job_id)
            print(f"\nFinal status: {final_status['status']}")
            if final_status['status'] == 'success':
                print(f"✅ Design ID: {final_status.get('design_id')}")
                print(f"✅ Design URL: {final_status.get('design_url')}")
            elif final_status['status'] == 'failed':
                print(f"❌ Error: {final_status.get('error')}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

