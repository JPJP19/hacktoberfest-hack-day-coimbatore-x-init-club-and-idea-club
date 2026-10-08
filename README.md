# WasteConnect 

> AI-powered recycling marketplace that connects waste generators with suitable recyclers through intelligent matching and competitive bidding.

## Team

**Team Name:** Vertex Zero


| Member | Contribution   |
| ------ | -------------- |
| A S Jeevanpranav | Backend development, database design, API integration, and transaction workflow |
| Dakshenya KS | Frontend development, UI/UX, marketplace and dashboard implementation |
| Mahizha S | AI/ML architecture, Gemma integration, semantic matching, and decision intelligence |
| Prajiin K | Recycler marketplace, bidding system, testing, integration, and deployment |


## Problem Statement

### The Problem

Recycling is often fragmented for both consumers and recycling vendors. Individuals who have recyclable materials such as e-waste, copper, aluminium, plastic, paper, or scrap metal often do not know which recycler to contact, what their waste is worth, or whether they are getting a fair offer. They may have to contact multiple local recyclers individually to compare prices.
At the same time, recycling vendors have difficulty discovering nearby sources of recyclable materials that match the materials they process.
This creates a disconnected ecosystem where potentially valuable recyclable materials may simply be discarded because finding the right recycler is inconvenient.

### Why We Chose This Problem

Recycling is usually treated as a disposal problem.We want to change that into a value and connectivity problem.
The idea is to make recycling as convenient as using a modern service marketplace. Instead of searching for recyclers manually, users can list their recyclable materials once and allow suitable recyclers to compete for them.
This can make recycling more convenient for users while helping recyclers discover a reliable supply of recyclable materials.

## Solution

We propose WasteConnect, a two-sided digital marketplace that connects people who have recyclable materials with recycling vendors.
Users can upload an image and description of their waste. Gemma analyzes the available information to understand the material and generate a structured waste listing.
The listing is then made available to eligible recycling vendors in the relevant area. Vendors can submit competing bids/offers based on the material, quantity, location, and their processing capabilities.
Users can compare the available offers based on:
- Price
- Distance
- Pickup availability
- Vendor rating
- Material compatibility
- Reliability

Gemma acts as a decision-support layer, helping users understand the trade-offs between different offers and explaining why a particular option may be more suitable.
The final decision remains with the user.

### Key Features

- AI-Powered Waste Understanding
- Competitive Bidding Marketplace
- Explainable Best-Offer Recommendations
- Safety, Trust and Transparent Transactions

## Innovation and Differentiation

Existing recycling systems often focus on collection or disposal, while WasteConnect focuses on creating a marketplace between waste generators and recyclers.
The key difference is the combination of:
AI-powered waste understanding + competitive recycler marketplace + intelligent offer comparison.
Instead of users searching for individual recycling vendors, the platform allows suitable vendors to come to the user through a competitive offer system.
Gemma is not used simply as a chatbot. It acts as an intelligence layer that understands unstructured waste information and helps users make informed decisions when comparing recycler offers.
## Technical Implementation

### Architecture

[Add the system architecture or workflow Mermaid diagram here.]

### Technology Stack


| Category        | Technologies                |
| --------------- | --------------------------- |
| Frontend        | [Technologies / N/A]        |
| Backend         | [Technologies / N/A]        |
| Database        | [Technologies / N/A]        |
| AI / ML         | [Models / frameworks / N/A] |
| Infrastructure  | [Technologies / N/A]        |
| APIs / Services | [Services / N/A]            |


If a category or technology is not implemented in the project, specify `N/A` instead of leaving the field blank.

### How It Works

WasteConnect operates as a two-sided marketplace connecting users with recyclable materials to recycling vendors.
1. Waste Listing: The user uploads an image and description of the recyclable material along with quantity and location.
2. AI Understanding: Gemma analyzes the submitted information to identify the likely waste category, material characteristics, and appropriate recycler category.
3. Recycler Matching: The backend filters recycling vendors based on material compatibility, service area, and availability.
4. Competitive Bidding: Eligible recyclers receive the listing and can submit offers containing their proposed price, pickup availability, and other relevant conditions.
5. Offer Comparison: Multiple offers are presented to the user. Gemma analyzes factors such as price, distance, pickup time, vendor rating, and material compatibility.
6. AI Recommendation: Gemma provides an explainable recommendation and describes the trade-offs between the available offers.
7. User Decision: The user makes the final selection and accepts a recycler's offer.
8. Pickup and Transaction: The selected recycler receives the request, pickup is scheduled, and the transaction status is updated through the platform.

### Technical Decisions

1. Gemma as the Intelligence Layer
Gemma is used for tasks requiring natural-language and multimodal understanding rather than deterministic operations.
It assists with:
- Understanding waste descriptions and images
- Extracting structured information from unstructured inputs
- Identifying suitable recycling categories
- Understanding recycler capabilities
- Comparing competing offers
- Explaining recommendations
Deterministic operations such as bidding, database updates, filtering, transaction states, and price calculations are handled by the backend.
2. Two-Sided Marketplace Architecture
The system separates the user and recycler workflows while connecting both through a common backend.
This allows users to create waste listings while recyclers can independently discover relevant listings and submit offers.
3. Competitive Offer Model
Instead of automatically assigning a recycler, multiple eligible recyclers can submit offers.
This gives users the ability to compare:
- Price
- Distance
- Pickup availability
- Rating
- Recycler compatibility
4. Explainable AI Recommendations
Gemma does not make an irreversible transaction decision.
Instead, it explains why an offer may be suitable and allows the user to make the final decision.
For example:
"Recycler B provides the highest price, while Recycler C offers faster pickup, shorter distance, and a higher vendor rating."

## Implementation During the Hackathon

During the Hack Day, the team implemented a functional prototype of WasteConnect demonstrating the complete recycling marketplace workflow.
The implemented prototype includes:
- User waste listing
- Waste image and description submission
- Gemma-based waste understanding
- Recycler profiles
- Recycler discovery
- Competitive bidding
- Bid comparison
- Gemma-powered offer analysis
- Explainable recycler recommendation
- Recycler selection
- Pickup status
- Transaction completion flow
- User and recycler dashboards

### Team Contributions

- **AS Jeevanpranav:** Backend development, database design, API integration, and transaction workflow
- **Dakshenya KS:** Frontend development, UI/UX, marketplace and dashboard implementation
- **Mahizha S:** AI/ML architecture, Gemma integration, semantic matching, and decision intelligence 
- **Prajiin K:** Recycler marketplace, bidding system, testing, integration, and deployment

## Working Application

**Live Application:** [Live URL]

[Briefly explain how the deployed application can be accessed and what functionality can be tested.]

The submitted application should be functional and accessible through the provided link where applicable.

## Demo Video

**Demo Video:** [Video URL]

[Provide a short demonstration of the working project, covering the main user flow and important functionality.]

## Open Source and AI Usage

### AI / Models

- **[Model]:** [How it is used]

### Open Source Components

- **[Library / Framework]:** [Purpose]
- **[Dataset]:** [Purpose]
- **[API / Service]:** [Purpose]

[Include relevant licenses, attribution, and acknowledgements for external components.]

## Setup and Usage

### Prerequisites

- [Requirement]
- [Requirement]

### Installation

```bash
git clone [repository-url]
cd [project-directory]
[installation-command]
```

### Environment Variables

```env
[VARIABLE_NAME]=[value]
```



### Running the Project

```bash
[run-command]
```

### Usage

[Explain the basic steps required to use the project.]

## Devpost Submission

**Devpost Project:** [Devpost Project URL]

[Add the link to the team's Devpost submission. Ensure the Devpost project page is complete and contains the required project information, links, media, and team details.]

## Credits and License

### Credits

[Credit libraries, frameworks, datasets, models, APIs, contributors, and other external resources used.]

### License

[License name and/or link.]

## Submission Checklist

- [ ] Project title and description added
- [ ] All team members listed
- [ ] Problem clearly explained
- [ ] Reason for choosing the problem explained
- [ ] Solution and key features documented
- [ ] Innovation and differentiation explained
- [ ] Architecture included
- [ ] Technical implementation documented
- [ ] Work completed during the hackathon documented
- [ ] Team contributions documented
- [ ] Working application is functional
- [ ] Live application link added where applicable
- [ ] Demo video added
- [ ] AI and open-source components documented
- [ ] Setup and usage instructions tested
- [ ] Challenges and learnings documented
- [ ] Devpost submission completed
- [ ] Devpost link added
- [ ] Credits added
- [ ] License added
- [ ] Repository is organized and complete
