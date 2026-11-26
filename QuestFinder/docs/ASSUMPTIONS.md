# QuestFinder: Assumptions and Clarifications (Deliverable 7)

Where the manuscript or the prototype (Figure 10) did not say exactly how something should work, this is
the interpretation used in the system.

## Confirmed with the team

1. **Barangay Admin approves verification.** A separate admin role reviews ID + face scans.
2. **One account for both roles.** Any member can post quests (client) and accept quests (task worker).
3. **Pay is reserved on acceptance and released on completion.** It comes out of the client's wallet when the
   client accepts a task worker and goes to the worker when the client marks the quest completed.
4. **Maps use Leaflet with OpenStreetMap tiles.**
5. **A client cannot accept their own quest.** Their own quests are hidden from their Quest list, the server
   refuses it, and the database has a check constraint for it.
6. **Identity verification = ID scan, then face scan to confirm the ID, strictly 18+.**
7. The name stays **QuestFinder**.
8. **Quests can only be pinned inside Brgy. San Vicente.** The boundary is the official OpenStreetMap barangay polygon (relation 15790886), saved in `app/data/`. The pin snaps back if dropped outside the outline, and the server rejects outside coordinates. A member's own location (used to measure distance) may be anywhere, because task workers can live in nearby barangays. It can be switched off with `RESTRICT_QUESTS_TO_BARANGAY=false`.

## Interpretations made while building

| # | Topic | Assumption |
|---|---|---|
| 1 | "Accept Quest" | The prototype's **ACCEPT QUEST** button means the worker offers to do the quest. The client then accepts one worker. Several workers may accept the same quest; the others are declined automatically when one is chosen. |
| 2 | Quest fields | Prototype Post fields (Location, Work Description, Qualification, Offered Pay, Upload Photo) plus **Title** and **Duration**, because both appear on the prototype's quest card and details screens. |
| 3 | Pay limits | ₱50 to ₱20,000 per quest (configurable in `.env`). |
| 4 | Distance | Straight-line (haversine) distance, not road distance. Before acceptance it is measured to the approximate point (shown as "~0.6 km"). |
| 5 | Location privacy | Other users see a random point 150–300 m from the real spot, kept inside the barangay where possible (a circle on the map) until the client accepts a worker; only the client and that worker see the exact pin and landmark. |
| 6 | Location source | GPS through the browser after a short explanation screen, or a pin placed on the map. Location is saved when the user saves it, not tracked continuously. Geofencing is not included. |
| 7 | Face matching | Runs in the browser with face-api (TensorFlow.js); only the score and the two images are sent. The server re-checks the score threshold, but the Barangay Admin's human review is the final decision. There is no liveness test beyond requiring a live camera capture for the face. |
| 8 | 18+ rule | Checked at registration, in the browser during verification, on the server (ID birthdate must match the account and be 18+), and again when the admin approves. |
| 9 | ID data stored | ID type, name and birthdate on the ID, and only the **last 4 characters** of the ID number. |
| 10 | Verification gate | Browsing is open to all members; posting, accepting, and deposit/withdraw need an approved verification (`REQUIRE_VERIFICATION=true`). |
| 11 | Wallet | Deposits and withdrawals are **simulated** (GCash, Maya, bank transfer labels). No payment gateway. |
| 12 | Cancellation | A client can cancel a quest only while no worker has been accepted. Cancelling or disputing an accepted quest is not in the manuscript and is not included. |
| 13 | Completion | Only the client marks a quest completed, since the client is the one confirming the work and releasing the pay. |
| 14 | Chat | Opens automatically when a client accepts a worker. New messages arrive by polling every 3 seconds (no WebSockets). Text and photo messages. |
| 15 | Notifications | In-app only (bell list): a worker accepted your quest, you were accepted, pay released, verification result. No SMS, email or push. |
| 16 | Ratings | Both sides can rate once per completed quest (1–5 stars + optional review). The average shows on profiles and when choosing a worker. |
| 17 | Skills | Chosen from a dropdown of local skills (up to 8), grouped by Home & repairs, Cleaning, Garden, Errands, Tech, Care, and Business. |
| 18 | Settings | Edit profile, My location, Identity verification, Change password, Log out. |
| 19 | My quests | Reached from Home ("My quests & applications"): **Posted** (with the number of workers who accepted) and **Accepted**. |
| 20 | Admin | The Barangay Admin uses a separate panel and does not post or accept quests. The admin can view all posted quests and users, suspend a member (1 hour to 365 days, with a reason shown to the user), and delete a member account. Deleting a task worker reopens the quests they were doing and returns the reserved pay to the clients; deleting a client removes their quests and notifies their workers. Admin accounts cannot be suspended or deleted from the panel. |
| 21 | Languages | Interface in English; Filipino may be used freely in quests and chat. |
