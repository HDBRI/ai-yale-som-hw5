# HW5 AI Prompts (prompt log)

**Student:** Ria Vijh · **Course:** AI, Yale SOM · **Coding assistant:** Claude Code (Claude Opus 5.5), one session on 2026-10-14

Each task lists its main prompt **verbatim** (typos kept), followed by any follow-up prompts that changed the work. Clarifying questions and file-housekeeping messages are left out.

## Task 1 — Set up HW5 folder & prompt log

**Prompt:**
> okay we are working on the AI assignment HW5 today, out all files in  taht folder, maintain a prompt log, do u remeber the format?

## Task 2 — Study the campus customs database

**Prompt:**
> task 2 - study the campus customs database - Open the data/campus_customs.db & look through every table & its fields. COpy the original file to data/campus_customs_new.db - later problems update that working copy.Study the three open tickets so you see how they link to other tables. Start output/harness.md - for each table list the fields & one short line on why that table matters for teh agents. We will keep grpwing the harness for later problems.

## Task 3 — Build the MCP server

**Prompt:**
> Task 3 - build teh MCP server - write an mcp server in mcp_server/ using FASTMCP. It will talk to data/campus_customs_new.db. You do not need to run it or connect in thsi probolem. every agent in this homework uses the tools in this MCP server. we will add more tools to it later, for now write 3 tools you know we will need for thr tickets in the database. Keep the names clear, never invent any data, only use info in the database. In output/harness.md, list each of your 3 MCP tools. For every tool include, whoch table it reads, which tciket it helps unlock (101, 102, 103)& one sentence on why that tool is the right one for that ticket.  Vague lines like 'low inventory' score low - tie the tool to the ticket. ALso add a short mcp_server/README.md file that explains what that MCP server is for, which database file it uses, & the 3 tools it has.

## Task 4 — Add the MCP server to the vibe coder & test each tool

**Prompt:**
> Task 4 - Add teh MCP server to thje vibe coder & test each tool - Add the mcp server to this project sp the vibe coder can call teh tools. Save the connection JSON text in .mcp.json at the project root (or however your vibe coder saves local MCP server lists). With your vibe coder connected, test each of the 3 tools. Save the evidence in output/mcp_smoke.json. For every tool include - the prompt I asked you, the tool name & the tool output (must match values in data/campus_customs_new.db)

**Follow-up prompts:**
> 1. Ticket 101 – check_stock: Can you check the current inventory for the Classic Bulldog Tee (SKU: CC-TEE-WHITE) in size Small and confirm whether we have enough stock to fulfill an order?

> 2. Ticket 102 – get_rent_due: For lease ID 1, can you find the upcoming rent payment amount and due date, and verify whether the available checking account balance is sufficient to pay it?

> 3. Ticket 103 – get_sku_pricing: Can you pull the unit cost and retail price for the Navy Bulldog Hoodie (SKU: CC-HOOD-NAVY) and calculate the maximum discount we could offer without selling below cost?

## Task 5 — Build the agent team & grow the MCP tools

**Prompt:**
> Task 5 - Build teh agent team & grow the MCP tools - Build the agentic team for Campus Customs using PydanticAI: Boss, Inventory, Accpunting, Faiclities, & Customer service. Include prompts, models, & agent loops so they can delegate work to each other with full connectivity - put the agent prompts in backend/prompts/ - one file per agent. Put data types in backend/models.py & the agent files under backend/ (layout can vary as long as the 5 roles are clear). Use portkeyapi & only gpt luna 6 for every agent. We will write eahc prompt in our own words with the shop rules that the agent needs. More detailed prompts that cover all aspects of an agent's work & scope will score higher than a short generic prompt. Add any tools the agent needs to the MCP server so they can work on the open tickets. Shop facts come from teh MCP server over data/campus_customs_new.db - do not invent a second shop tools layer that bypasses MCP. Wite the agents so they append to output/aduit_trail.json as they run - for each agent loop step, record enough to audit later. Append to this file - do not wipe it each run. In ouput/harness.md list each agent & each MCP tool incuding the ones we add in this problem along with which table the tool uses. ALso add a short safety section - the guardrails a real business would want when agents touch real customers & real money plus limits that keep token use in check. Update mcp_server/README.md so the tool list matches what you have now.

## Task 6 — Plan the 3 tickets

**Prompt:**
> Task 6 - plan the 3 tickets - before you wire the the backend, write down what you expect the team to do on each open ticket. Build output/desk_tickets.html - a page I can double click with one tab per ticket (101, 102, 103). Also add empty cash & reflection tabs for later problems (leave them black or with a short coming later note for now). On each ticket tab, fill an Expected section only - leave room for an Actual section you will fill after you run the agents). For each ticket's expected section - write who the boss shoudl call first & why, all the agent delegationss you expect - not "Boss calls everyone" & which MCP tools you expect taht run to use. Plans that send every specialist on every ticket score low. you will compare this plan to what actually happens when your agent resolves the 3 tickets.

## Task 7 — Backend routes

**Prompt:**
> Task 7 - Backend routes - Your react frontend dashboard (the next problem) needs a backend it can call. In backend/main.py, use FASTAPI & add routes that do the following: Return the three tickets and whether each is open or resolved Take a ticket id and run your agent team on that ticket, Return recent agent events — what each agent said and which tools they used — so the board can refresh, Approve a payment or purchase after a human clicks approve (agents only prepare the pay; this route is what actually changes cash), Return the current checking balance from cash_accounts, Reset the database to the original values when you want to try a fresh run. From the backend/  folder, start the server with 'uvicorn main:app --reload --port 8000'. This turns on your backend at http://localhost:8000 so the frontend dashboard can call those routes. In output/harness.md list each route in one line (what URL/ what it does).

## Task 8 — Frontend dashboard

**Prompt:**
> Task 8 - Build the frontend dashboard in frontend/ with react + vite + typeScript. The page should call the routes you built in prob 7. At min the board should list all 3 tickets, let u pick one ticket & start the agent team on it, show each agent & what they are saying / doing while the ticket runs, mark a ticket resolved when the run finishes, show a short summary of what each agent did on that ticket, let a human approve a pay or purchase when asked, show the checking balance (it should drop after an approved pay). Make the dashboard look good. Be creative with the layout & feel - this is a real desk people would want to sit at, so put thought into how it looks. Tell the frontend to talk to teh backend at http://llocalhost:8000. On the backend, allow the vite page origin (usually http://localhost:5173) so the browser is allowed to call those routes. Start the board with - npm run dev. This opens the react desk in your browser so you can pick tickets & watch agents. Write output/design.md with what you chose for the dashboard look (layput, how agents read differently, how resolved tickets & cash show up) & why - including the creative choices that make it feel special & something humans would atcually enjoy using).

## Task 9 — Resolve the tickets

**Prompt:**
> Taks 9 - resolve the tickets - Before testing the agent on a full run over the three tickets, reset the working database data/campus_customs_new.db again so you start clean. Note teh starting checking balance. Then run all 3 tickets on the board (101, 102, 103) until each one is resolved. Open ouput/desk_tickets.html from prob 6. On each ticket tab, fill the actual section from this run: which agents worked, waht they delegated, & which tools they used. Keep your expected section so you can compare teh 2. On the cash tab of the same output/desk_tickets.html, itemize the money: Starting checking balance (after the reset), For each ticket: how cash changed when that ticket resolved, and why (which pay / purchase, dollar amount), Ending checking balance — it must match `cash_accounts` in the working database, Wrong cash math loses points even if the board shows every ticket resolved. Also save: `output/resolved_tickets.json`, for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals `output/resolved_board.html` - a page you can double-click with a screenshot of your React board for each resolved ticket (101, 102, and 103) And Append real runs to `output/audit_trail.json`. Finish `output/harness.md` so it covers tables, MCP tools, the five agents, API routes, the dashboard, and safety rules.

## Task 10 — Reflections

**Prompt:**
> Task 10 - Open output/desk_tickets.html & fill teh reflections tab. Answer in your own vibe & be detailed & thorough - 1. How would you evaluate the performance of the agents on each ticket & why? 2. For each ticket, how did Actual compare to the Expected plan you wrote earlier? 3. what would have been simpler as one agent with tools - & why? 4. Describe 3 new problems Campus customs might face that this agent team could solve with the tools you built, 5. Describe three new problems Campus customs might face that this agent team cpuld not solve with the tools you built, & explain the tools & agents you would need to solve them. Tie every answer to this app & the 3 tickets you ran - use the ticket tabs & the cash tab on the same page as your evdence. Generic AI essays without campus customs details will score low.

## Task 11 — Submit to GitHub

**Prompt:**
> Expected file layout: [screenshot, transcribed: hw5/ with AI_prompts.md, requirements.txt, .env.example, .gitignore, .mcp.json, README.md, data/ (campus_customs.db, campus_customs_new.db), mcp_server/ (server.py, README.md), frontend/, backend/ (main.py, models.py, prompts/ boss.md, inventory.md, accounting.md, facilities.md, customer_service.md), output/ (harness.md, mcp_smoke.json, desk_tickets.html, design.md, resolved_tickets.json, resolved_board.html, audit_trail.json, github_url.txt)]. README should explain: copy original DB to the working copy when you need a clean run, start MCP server, start FastAPI backend, start the React board, reset the DB before a full three-ticket run.
> Push the code to a public GitHub repository so graders can clone it. Submit the repo URL to Canvas & also put it in output/github_url.txt. Do not push the real .env to the Github repo. Include both database files under data/ (the original & your working copy) so graders can run your app easily.
