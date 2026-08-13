import os
import re
from pathlib import Path
from typing import Dict, Any

import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:/Program Files/Tesseract-OCR/tesseract.exe"
)
from PIL import Image

from langchain_ollama import ChatOllama

from app.agents.entity_extraction import run_entity_extraction


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "llama3.2:3b"

llm = ChatOllama(
    model=MODEL_NAME,
    temperature=0,
)


# ============================================================
# OCR
# ============================================================

def extract_text_from_image(image_path: str) -> str:
    """
    Extract visible text from a screenshot using Tesseract OCR.
    """

    image = Image.open(image_path)

    # Upscale slightly to improve OCR on small UI text.
    width, height = image.size

    image = image.resize(
        (width * 2, height * 2)
    )

    text = pytesseract.image_to_string(
        image,
        config="--psm 6",
    )

    return text.strip()


# ============================================================
# CHAT SUMMARY
# ============================================================

def summarize_chat(ocr_text: str) -> str:
    """
    Generate a short investigator-facing summary from OCR text.
    """

    prompt = f"""
You are assisting a digital investigator.

Below is OCR text extracted from a synthetic chat screenshot.

Summarize the conversation in 2-4 concise sentences.

Focus on:
- who is communicating
- important events
- actions mentioned
- locations mentioned
- anything potentially relevant to an investigation

Do not invent facts that are not present.

OCR TEXT:
{ocr_text}
"""

    response = llm.invoke(prompt)

    return response.content.strip()


# ============================================================
# HEADER INFORMATION
# ============================================================

def extract_header_information(ocr_text: str) -> Dict[str, Any]:
    """
    Extract simple metadata visible in the messaging header.
    """

    result = {
        "contact_name": None,
        "last_seen": None,
    }

    lines = [
        line.strip()
        for line in ocr_text.splitlines()
        if line.strip()
    ]

    # Look for a line resembling:
    # "last seen today at 9:15PM"
    for line in lines:

        lower = line.lower()

        if "last seen" in lower:
            result["last_seen"] = line

    # The screenshot's contact name is normally near the top.
    # We look for the first meaningful line before "last seen".
    for index, line in enumerate(lines):

        if "last seen" in line.lower():

            if index > 0:
                candidate = lines[index - 1]

                # Avoid treating UI text as a person name.
                ignored = {
                    "whatsapp",
                    "instagram",
                    "messenger",
                    "online",
                }

                if candidate.lower() not in ignored:
                    result["contact_name"] = candidate

            break

    return result


# ============================================================
# PROFILE PICTURE
# ============================================================

def extract_profile_picture(
    image_path: str,
    output_directory: str,
) -> str | None:
    """
    Crop the contact profile picture from the messaging header.

    This does NOT identify the person in the profile picture.
    It simply preserves the visual evidence for investigators.
    """

    image = Image.open(image_path)

    width, height = image.size

    # Approximate WhatsApp-style header location.
    #
    # For this PoC screenshot:
    # profile image is around x=85-125, y=65-105.
    #
    # We use a slightly larger crop so the complete avatar is retained.
    left = int(width * 0.15)
    top = int(height * 0.055)
    right = int(width * 0.27)
    bottom = int(height * 0.12)

    profile = image.crop(
        (left, top, right, bottom)
    )

    os.makedirs(
        output_directory,
        exist_ok=True,
    )

    output_path = os.path.join(
        output_directory,
        "profile_picture.png",
    )

    profile.save(output_path)

    return output_path


# ============================================================
# COMPLETE IMAGE EVIDENCE PIPELINE
# ============================================================

def run_image_entity_extraction(
    case_id: str,
    evidence_id: str,
    image_path: str,
    profile_output_directory: str = "data/extracted",
) -> Dict[str, Any]:

    print("\n" + "=" * 60)
    print("ENTITY EXTRACTION — IMAGE EVIDENCE")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. OCR
    # --------------------------------------------------------

    print("[1/4] Running OCR...")

    ocr_text = extract_text_from_image(
        image_path
    )

    print("\nOCR TEXT:")
    print(ocr_text)

    # --------------------------------------------------------
    # 2. Header metadata
    # --------------------------------------------------------

    print("\n[2/4] Extracting header metadata...")

    header = extract_header_information(
        ocr_text
    )

    print("Contact:", header["contact_name"])
    print("Last seen:", header["last_seen"])

    # --------------------------------------------------------
    # 3. Existing Entity Extraction Agent
    # --------------------------------------------------------

    print("\n[3/4] Running Entity Extraction Agent...")

    entity_result = run_entity_extraction(
        case_id=case_id,
        evidence_id=evidence_id,
        evidence_text=ocr_text,
    )

    entities = entity_result.get(
        "entities",
        [],
    )

    # --------------------------------------------------------
    # 4. Chat summary
    # --------------------------------------------------------

    print("\n[4/4] Generating investigation summary...")

    summary = summarize_chat(
        ocr_text
    )

    # --------------------------------------------------------
    # 5. Preserve profile picture
    # --------------------------------------------------------

    profile_path = extract_profile_picture(
        image_path=image_path,
        output_directory=profile_output_directory,
    )

    print("\n" + "=" * 60)
    print("IMAGE EXTRACTION COMPLETE")
    print("=" * 60)

    return {
        "evidence_id": evidence_id,
        "ocr_text": ocr_text,
        "header": header,
        "entities": entities,
        "summary": summary,
        "profile_picture": profile_path,
    }