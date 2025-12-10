
import socket
import requests
import sys

def check_connection():
    project_ref = "nnplwknnfvtiqqfvfxww"
    db_host = f"db.{project_ref}.supabase.co"
    api_url = f"https://{project_ref}.supabase.co"
    
    print(f"1. Checking API ({api_url})...")
    try:
        response = requests.get(api_url, timeout=5)
        print(f"   Response: {response.status_code}")
        if response.status_code == 200:
             print("   API is UP (Project likely active)")
        elif response.status_code == 503:
             print("   API 503 (Project might be PAUSED)")
        else:
             print(f"   API Status: {response.status_code}")
    except Exception as e:
        print(f"   API Check Failed: {e}")
        
    print(f"\n2. Checking DB Host DNS ({db_host})...")
    try:
        ip = socket.gethostbyname(db_host)
        print(f"   DNS OK. Resolved to: {ip}")
    except socket.gaierror as e:
        print(f"   DNS FAILED: {e}")
        print("   (This means the hostname doesn't exist)")
        
    print(f"\n3. Checking Alternative Host (Direct Ref: {project_ref}.supabase.co)...")
    try:
        ip = socket.gethostbyname(f"{project_ref}.supabase.co")
        print(f"   Alternate DNS OK. Resolved to: {ip}")
    except socket.gaierror:
        print("   Alternate DNS FAILED")

if __name__ == "__main__":
    check_connection()
