import os
import re
from google.cloud import vision

# ✅ Set credentials only for local development
# When deployed to Google Cloud, credentials are automatically detected
if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS') and not os.getenv('GOOGLE_CLOUD_PROJECT'):
    # Only set this path when running locally
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "fixhub-vision-abf5b2d67e46.json"

# ✅ Initialize Google Vision API Client
try:
    client = vision.ImageAnnotatorClient()
    print("✅ Google Vision API client initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Vision API client: {e}")
    client = None

def extract_text(image_path):
    """
    Extracts text from an image using Google Vision API.
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        str: Extracted text or error message
    """
    if not client:
        return "❌ Vision API client not initialized"
        
    try:
        # Check if file exists
        if not os.path.exists(image_path):
            return "❌ Image file not found"
            
        # Read the image file
        with open(image_path, "rb") as image_file:
            content = image_file.read()
            
        # Create vision image object
        image = vision.Image(content=content)
        
        # Perform text detection
        response = client.text_detection(image=image)
        
        # Check for API errors
        if response.error.message:
            return f"❌ Vision API Error: {response.error.message}"
            
        # Extract text annotations
        texts = response.text_annotations
        
        if texts:
            # Return the first (most comprehensive) text annotation
            return texts[0].description.strip()
        else:
            return "❌ No text found in image"
            
    except FileNotFoundError:
        return "❌ Image file not found"
    except PermissionError:
        return "❌ Permission denied accessing image file"
    except Exception as e:
        return f"❌ Error processing image: {str(e)}"

def extract_name_and_dob(text):
    """
    Extract Name and Date of Birth from text using regex patterns.
    
    Args:
        text (str): Text extracted from document
        
    Returns:
        tuple: (name, dob) - both as strings
    """
    if not text or text.startswith("❌"):
        return "Not Found", "Not Found"
    
    # Enhanced regex patterns for name extraction
    name_patterns = [
        r"Name[:\s]+([A-Za-z\s]+?)(?:\n|$)",  # Name: followed by text until newline
        r"Name[:\s]*([A-Za-z\s]{2,50})",      # Name: followed by 2-50 characters
        r"(?:Name|NAME)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # Proper case names
    ]
    
    # Enhanced regex patterns for DOB extraction
    dob_patterns = [
        r"DOB[:\s]+(\d{2}[\/\-]\d{2}[\/\-]\d{4})",  # DOB: DD/MM/YYYY or DD-MM-YYYY
        r"DOB[:\s]+(\d{4}[\/\-]\d{2}[\/\-]\d{2})",  # DOB: YYYY/MM/DD or YYYY-MM-DD
        r"Date of Birth[:\s]+(\d{2}[\/\-]\d{2}[\/\-]\d{4})",  # Full "Date of Birth"
        r"Date of Birth[:\s]+(\d{4}[\/\-]\d{2}[\/\-]\d{2})",
        r"(?:DOB|Date of Birth)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})",  # Flexible spacing
    ]
    
    # Try to find name using multiple patterns
    name = "Not Found"
    for pattern in name_patterns:
        name_match = re.search(pattern, text, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip()
            # Clean up the name (remove extra spaces, newlines)
            name = ' '.join(name.split())
            break
    
    # Try to find DOB using multiple patterns
    dob = "Not Found"
    for pattern in dob_patterns:
        dob_match = re.search(pattern, text, re.IGNORECASE)
        if dob_match:
            dob = dob_match.group(1).strip()
            break
    
    return name, dob

def verify_documents(aadhaar_path, proof_path):
    """
    Verify identity by comparing Aadhaar and proof documents.
    
    Args:
        aadhaar_path (str): Path to Aadhaar image
        proof_path (str): Path to proof document image
        
    Returns:
        dict: Verification result with status and details
    """
    print(f"🔍 Processing Aadhaar: {aadhaar_path}")
    print(f"🔍 Processing Proof: {proof_path}")
    
    # Extract text from both documents
    aadhaar_text = extract_text(aadhaar_path)
    proof_text = extract_text(proof_path)
    
    # Check if text extraction was successful
    if aadhaar_text.startswith("❌"):
        return {
            "status": "failed",
            "message": f"Aadhaar processing failed: {aadhaar_text}",
            "details": {}
        }
    
    if proof_text.startswith("❌"):
        return {
            "status": "failed", 
            "message": f"Proof document processing failed: {proof_text}",
            "details": {}
        }
    
    # Extract name and DOB from both documents
    aadhaar_name, aadhaar_dob = extract_name_and_dob(aadhaar_text)
    proof_name, proof_dob = extract_name_and_dob(proof_text)
    
    # Prepare verification details
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
    
    print(f"\n📋 Extracted Details:")
    print(f"🆔 Aadhaar - Name: {aadhaar_name} | DOB: {aadhaar_dob}")
    print(f"📄 Proof - Name: {proof_name} | DOB: {proof_dob}")
    
    # Check if essential information was found
    if aadhaar_name == "Not Found" or proof_name == "Not Found":
        return {
            "status": "failed",
            "message": "❌ Could not extract name from one or both documents. Please ensure images are clear and contain readable text.",
            "details": details
        }
    
    if aadhaar_dob == "Not Found" or proof_dob == "Not Found":
        return {
            "status": "failed",
            "message": "❌ Could not extract date of birth from one or both documents. Please ensure images are clear and contain readable text.",
            "details": details
        }
    
    # Compare names (case-insensitive)
    names_match = aadhaar_name.lower().strip() == proof_name.lower().strip()
    dobs_match = aadhaar_dob == proof_dob
    
    if names_match and dobs_match:
        return {
            "status": "verified",
            "message": "✅ Identity verification successful! Names and dates of birth match.",
            "details": details
        }
    else:
        mismatch_details = []
        if not names_match:
            mismatch_details.append(f"Names don't match ('{aadhaar_name}' vs '{proof_name}')")
        if not dobs_match:
            mismatch_details.append(f"DOBs don't match ('{aadhaar_dob}' vs '{proof_dob}')")
        
        return {
            "status": "failed",
            "message": f"❌ Identity verification failed: {', '.join(mismatch_details)}",
            "details": details
        }

# ✅ Main execution (for standalone testing)
if __name__ == "__main__":
    print("🚀 FixHub Identity Verification System")
    print("=" * 50)
    
    # Check if Vision API is available
    if not client:
        print("❌ Cannot proceed without Vision API client")
        exit(1)
    
    # Get file paths from user
    aadhaar_path = input("🔹 Enter Aadhaar image path: ").strip().strip('"')
    proof_path = input("🔹 Enter Proof document image path: ").strip().strip('"')
    
    # Verify documents
    result = verify_documents(aadhaar_path, proof_path)
    
    # Display results
    print("\n" + "=" * 50)
    print("📊 VERIFICATION RESULTS")
    print("=" * 50)
    print(f"Status: {result['status'].upper()}")
    print(f"Message: {result['message']}")
    
    if result['details']:
        print(f"\n📋 Details:")
        print(f"Aadhaar Name: {result['details']['aadhaar']['name']}")
        print(f"Aadhaar DOB: {result['details']['aadhaar']['dob']}")
        print(f"Proof Name: {result['details']['proof']['name']}")
        print(f"Proof DOB: {result['details']['proof']['dob']}")
    
    print("=" * 50)