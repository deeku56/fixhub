import os
import re
import json
from google.cloud import vision
from google.oauth2 import service_account

# ✅ Initialize Google Vision API client
client = None
try:
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
        # ✅ Render deployment – Load credentials from environment variable
        creds_info = json.loads(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"))
        credentials = service_account.Credentials.from_service_account_info(creds_info)
        client = vision.ImageAnnotatorClient(credentials=credentials)
        print("✅ Google Vision API client initialized from JSON env variable")

    elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        # ✅ Local development – Load credentials from file path
        client = vision.ImageAnnotatorClient()
        print("✅ Google Vision API client initialized from credentials file")

    else:
        raise ValueError("❌ No Google Vision credentials found")

except Exception as e:
    print(f"❌ Failed to initialize Vision API client: {e}")
    client = None

def extract_text(image_path):
    """Extracts text from an image using Google Vision API."""
    if not client:
        return "❌ Vision API client not initialized"

    try:
        if not os.path.exists(image_path):
            return "❌ Image file not found"

        with open(image_path, "rb") as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        response = client.text_detection(image=image)

        if response.error.message:
            return f"❌ Vision API Error: {response.error.message}"

        texts = response.text_annotations
        return texts[0].description.strip() if texts else "❌ No text found in image"

    except FileNotFoundError:
        return "❌ Image file not found"
    except PermissionError:
        return "❌ Permission denied accessing image file"
    except Exception as e:
        return f"❌ Error processing image: {str(e)}"

def extract_name_and_dob(text):
    """Extract Name and Date of Birth from OCR text."""
    if not text or text.startswith("❌"):
        return "Not Found", "Not Found"

    name_patterns = [
        r"Name[:\s]+([A-Za-z\s]+?)(?:\n|$)",
        r"Name[:\s]*([A-Za-z\s]{2,50})",
        r"(?:Name|NAME)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
    ]
    dob_patterns = [
        r"DOB[:\s]+(\d{2}[\/\-]\d{2}[\/\-]\d{4})",
        r"DOB[:\s]+(\d{4}[\/\-]\d{2}[\/\-]\d{2})",
        r"Date of Birth[:\s]+(\d{2}[\/\-]\d{2}[\/\-]\d{4})",
        r"Date of Birth[:\s]+(\d{4}[\/\-]\d{2}[\/\-]\d{2})",
        r"(?:DOB|Date of Birth)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})",
    ]

    name = "Not Found"
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = ' '.join(match.group(1).strip().split())
            break

    dob = "Not Found"
    for pattern in dob_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            dob = match.group(1).strip()
            break

    return name, dob

def verify_documents(aadhaar_path, proof_path):
    """Compare Aadhaar and Proof to verify identity."""
    print(f"🔍 Aadhaar: {aadhaar_path}")
    print(f"🔍 Proof: {proof_path}")

    aadhaar_text = extract_text(aadhaar_path)
    proof_text = extract_text(proof_path)

    if aadhaar_text.startswith("❌"):
        return {"status": "failed", "message": f"Aadhaar error: {aadhaar_text}", "details": {}}
    if proof_text.startswith("❌"):
        return {"status": "failed", "message": f"Proof error: {proof_text}", "details": {}}

    aadhaar_name, aadhaar_dob = extract_name_and_dob(aadhaar_text)
    proof_name, proof_dob = extract_name_and_dob(proof_text)

    details = {
        "aadhaar": {
            "name": aadhaar_name,
            "dob": aadhaar_dob,
            "text_preview": aadhaar_text[:100] + "..." if len(aadhaar_text) > 100 else aadhaar_text
        },
        "proof": {
            "name": proof_name,
            "dob": proof_dob,
            "text_preview": proof_text[:100] + "..." if len(proof_text) > 100 else proof_text
        }
    }

    print("\n📋 Extracted:")
    print(f"🆔 Aadhaar – Name: {aadhaar_name}, DOB: {aadhaar_dob}")
    print(f"📄 Proof – Name: {proof_name}, DOB: {proof_dob}")

    if aadhaar_name == "Not Found" or proof_name == "Not Found":
        return {
            "status": "failed",
            "message": "❌ Name not found in one or both documents.",
            "details": details
        }

    if aadhaar_dob == "Not Found" or proof_dob == "Not Found":
        return {
            "status": "failed",
            "message": "❌ DOB not found in one or both documents.",
            "details": details
        }

    names_match = aadhaar_name.lower() == proof_name.lower()
    dobs_match = aadhaar_dob == proof_dob

    if names_match and dobs_match:
        return {
            "status": "verified",
            "message": "✅ Identity verification successful!",
            "details": details
        }

    mismatches = []
    if not names_match:
        mismatches.append(f"Names mismatch: '{aadhaar_name}' vs '{proof_name}'")
    if not dobs_match:
        mismatches.append(f"DOBs mismatch: '{aadhaar_dob}' vs '{proof_dob}'")

    return {
        "status": "failed",
        "message": "❌ Identity verification failed: " + ", ".join(mismatches),
        "details": details
    }

# ✅ For manual testing (optional)
if __name__ == "__main__":
    print("🚀 FixHub Identity Verification CLI")
    print("=" * 50)

    if not client:
        print("❌ Cannot continue. Vision API not initialized.")
        exit(1)

    aadhaar_path = input("🔹 Aadhaar Image Path: ").strip().strip('"')
    proof_path = input("🔹 Proof Image Path: ").strip().strip('"')

    result = verify_documents(aadhaar_path, proof_path)

    print("\n📊 VERIFICATION RESULTS")
    print("=" * 50)
    print(f"Status: {result['status'].upper()}")
    print(f"Message: {result['message']}")
    if result['details']:
        print("Aadhaar Name:", result['details']['aadhaar']['name'])
        print("Aadhaar DOB:", result['details']['aadhaar']['dob'])
        print("Proof Name:", result['details']['proof']['name'])
        print("Proof DOB:", result['details']['proof']['dob'])
    print("=" * 50)
