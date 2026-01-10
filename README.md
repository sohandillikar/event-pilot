Build a fully-equipped voice agent for corporate event planning.

Flow:

1. User calls the agent on phone
2. Agent greets the user and asks questions to extract the following information:
   - User's name
   - User's company name
   - User's role/occupation
   - Event name
   - Start date (YYYY-MM-DD format)
   - End date (YYYY-MM-DD format)
   - Number of attendes (int)
   - Event type (Give examples like conference, team offsite, training/workshop, holiday party, client event, board meeting, etc.)
   - Location City
   - Location State
   - Budget (int)
   - Required amenities/accomidations (Optional)
   - Additional details (Optional)
3. Agent saves all the information to MongoDB Atlas
4. Agent uses a custom web search tool to search for venues in the given location that match user needs
5. Agent saves all matching venues in MongoDB Atlas
6. Agent texts all the venue information to the user's phone number
7. Agent tells the user that they will contact all the venues to check for availibility, then get back to the user
8. Agent ends the call

Tech stack:
Language: Python
LLM: GPT-4o
Voice agent: Vapi
Web search: Tavily
SMS: Plivo
Database: MongoDB Atlas
