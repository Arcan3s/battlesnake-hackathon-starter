# Battlesnake Hackathon Starter Project

This is the starting template for the [Carleton Computer Science Society's](https://ccss.carleton.ca/) 2025 [Battlesnake Hackathon](https://ccss.carleton.ca/events/2025-2026/2025-09-13-battlesnake-hackathon/).

<img width="1000" alt="image" src="https://i.imgur.com/17V1Ksn.png" />

## Getting Started

### 1. Create Your Replit
Click the button below to create a Replit project from this template:

[![Run on Replit](https://repl.it/badge/github/BattlesnakeOfficial/starter-snake-python)](https://replit.com/@MathyouMB/battlesnake-hackathon-starter)

You **will NEED** to have a Replit account in order to "remix" the project template.

---

### 2. Get Your Public Replit URL

Once you open your project in Replit, use the **Network Manager** to retrieve your **Replit URL**.

Start by clicking the **+** (new tab) icon:

<img width="2226" height="1148" alt="image" src="https://github.com/user-attachments/assets/804a8a41-8a3d-467f-b0a4-b5e785703f48" />

Then search for the **"Networking"**:

<img width="2212" height="1140" alt="image" src="https://github.com/user-attachments/assets/2e217108-f3ed-4fae-90fe-ca217452da85" />

On the Network Manager, copy your **Replit URL**:

<img width="2208" height="1128" alt="image" src="https://github.com/user-attachments/assets/a8299d4f-4c6b-4912-a5a3-b3b83735bb39" />

---

### 3. Configure Your `.env` File

Once you have your **Replit URL**, add it to your `.env` file.

Start by opening the file explorer by clicking the icon in the top right:

<img width="2226" height="1154" alt="image" src="https://github.com/user-attachments/assets/e71ba439-fad6-458a-9065-6898c3cd9ae4" />

Click on the `.env` file in the file explorer and paste your Replit URL as shown:

<img width="2222" height="1152" alt="image" src="https://github.com/user-attachments/assets/ac9d2a52-abd1-456d-a409-a4b24fef71bb" />

---

### 4. Test Your Snake

Once you've configured your **Replit URL**, you're ready to test your snake.

Start by opening a new tab and opening the **Workflow Manager**:

<img width="2224" height="1146" alt="image" src="https://github.com/user-attachments/assets/4cc55f22-9d18-43f9-826f-44a6859a0a4a" />

Then Click **"Run Your Snake Webserver"**, and optionally click **Run 3 Test Snake Webservers** if you'd like to see your snake compete against the test snakes in `./examples`:

<img width="2222" height="1146" alt="image" src="https://github.com/user-attachments/assets/ef8fe40a-4679-494c-bd89-63f65f6d4dae" />

To see your snakes battle, click "Test Your Snake" to get begin the match:

<img width="2224" height="1148" alt="image" src="https://github.com/user-attachments/assets/e7347474-9d35-4a72-ae51-09597f19a299" />

**NOTE:** It may take a moment for the board to pop up in your browser.

If everything is setup correctly, a window should promptly open in your browser with a visualization of your snake.

<img width="1275" height="721" alt="Screenshot 2025-08-31 at 4 41 22 PM" src="https://github.com/user-attachments/assets/838ae8ab-567f-4dd0-825d-ffef4f0b50ed" />

If you want to run another match, you're need to stop then start the "Test Your Snake" workflow:

<img width="2332" height="1198" alt="image" src="https://github.com/user-attachments/assets/d8fc2ec0-af21-4eed-933d-086387d0b52a" />

While your snake is running, you can see the console output of your snake and the 3 test snakes in `./examples` in the console tab:

<img width="3434" height="1754" alt="image" src="https://github.com/user-attachments/assets/74270c69-98e9-4f63-9473-2209084a9593" />


---

## Coding Your Snake

To start coding your snake, open the **`main.py`** file (this is where your snakes' logic lives):

<img width="3452" height="1782" alt="image" src="https://github.com/user-attachments/assets/b8ebce02-3bd2-4ea2-87fb-99e2d430af12" />

The most important function is `move(game_state)`. 

Battlesnake calls this every turn and sends you a JSON payload (`game_state`) describing the current board and your snake (an example of that request is shown in the [Battlesnake docs](https://docs.battlesnake.com/api/example-move).

Your job is to read that data and return one of: "up", "down", "left", or "right".

For example, this code would result in your snake going down every turn.

```python
def move(game_state: typing.Dict) -> typing.Dict:
   return {"move": "down"}
```

When you modify `main.py`, make sure you **ALWAYS** stop, then start your **Snake Webserver** via the workflow page:

<img width="2342" height="1212" alt="image" src="https://github.com/user-attachments/assets/319d8573-517e-4ba2-a456-4365c9db8c6f" />






## Environment Health Check

Having trouble getting your snake running?  

Click the arrow next to the **Run** button, then select **Run Environment Health Check**.

<img width="500" alt="image" src="https://github.com/user-attachments/assets/1545f5fa-d15b-4703-805d-e6cae2655ca8" />

This will run a script that scans your environment and reports anything that might be missing or misconfigured:

<img width="900" alt="image" src="https://github.com/user-attachments/assets/d28caa0a-ad30-41da-bf25-7b5b3a2ac510" />


