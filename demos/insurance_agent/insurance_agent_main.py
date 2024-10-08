import openai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
openai.api_base = "http://127.0.0.1:10000/v1"  # Local proxy

# Data models
# Define a Pydantic model for the incoming request
class Message(BaseModel):
    role: str
    content: str

class Conversation(BaseModel):
    messages: list[Message]

class PolicyCoverageRequest(BaseModel):
    policy_type: str = Field(..., description="The type of a policy held by the customer For, e.g. car, boat, house, motorcycle)")

class PolicyInitiateRequest(PolicyCoverageRequest):
    deductible: float = Field(..., description="The deductible amount set of the policy")

class ClaimUpdate(BaseModel):
    claim_id: str
    notes: str  # Status or details of the claim

class DeductibleUpdate(BaseModel):
    policy_id: str
    deductible: float

class CoverageResponse(BaseModel):
    policy_type: str
    coverage: str  # Description of coverage
    premium: float  # The premium cost

# Get information about policy coverage
@app.post("/policy/coverage", response_model=CoverageResponse)
async def get_policy_coverage(req: PolicyCoverageRequest):
    """
    Retrieve the coverage details for a given policy type (car, boat, house, motorcycle).
    """
    policy_coverage = {
        "car": {"coverage": "Full car coverage with collision, liability", "premium": 500.0},
        "boat": {"coverage": "Full boat coverage including theft and storm damage", "premium": 700.0},
        "house": {"coverage": "Full house coverage including fire, theft, flood", "premium": 1000.0},
        "motorcycle": {"coverage": "Full motorcycle coverage with liability", "premium": 400.0},
    }

    if req.policy_type not in policy_coverage:
        raise HTTPException(status_code=404, detail="Policy type not found")

    return CoverageResponse(
        policy_type=req.policy_type,
        coverage=policy_coverage[req.policy_type]["coverage"],
        premium=policy_coverage[req.policy_type]["premium"]
    )

# Initiate policy coverage
@app.post("/policy/initiate")
async def initiate_policy(policy_request: PolicyInitiateRequest):
    """
    Initiate policy coverage for a car, boat, house, or motorcycle.
    """
    if policy_request.policy_type not in ["car", "boat", "house", "motorcycle"]:
        raise HTTPException(status_code=400, detail="Invalid policy type")

    return {"message": f"Policy initiated for {policy_request.policy_type}", "deductible": policy_request.deductible}

# Update claim details
@app.post("/policy/claim")
async def update_claim(req: ClaimUpdate):
    """
    Update the status or details of a claim.
    """
    # For simplicity, this is a mock update response
    return {"message": f"Claim {claim_update.claim_id} for policy {claim_update.claim_id} has been updated",
            "update": claim_update.notes}

# Update deductible amount
@app.post("/policy/deductible")
async def update_deductible(deductible_update: DeductibleUpdate):
    """
    Update the deductible amount for a specific policy.
    """
    # For simplicity, this is a mock update response
    return {"message": f"Deductible for policy {deductible_update.policy_id} has been updated",
            "new_deductible": deductible_update.deductible}

# Post method for policy Q/A
@app.post("/policy/qa")
async def policy_qa(conversation: Conversation):
    """
    This method handles Q/A related to general issues in insurance.
    It forwards the conversation to the OpenAI client via a local proxy and returns the response.
    """
    try:
        # Get the latest user message from the conversation
        user_message = conversation.messages  # Assuming the last message is from the user

        # Call the OpenAI API through the Python client
        response = openai.Completion.create(
            model="gpt-4o",  # Replace with the model you want to use
            prompt=user_message,
            max_tokens=150
        )

        # Extract the response text from OpenAI
        completion = response.choices[0].text.strip()

        # Build the assistant's response message
        assistant_message = Message(role="assistant", content=completion)

        # Append the assistant's response to the conversation and return it
        updated_conversation = Conversation(
            messages=conversation.messages + [assistant_message]
        )

        return updated_conversation

    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# Run the app using:
# uvicorn main:app --reload
