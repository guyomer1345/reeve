# Phase 12 — the original request, verbatim

**The source of the acceptance ledger in `11-roadmap.md`.** Recovered 2026-09-14 from session
`257d8bf7` after five of its ten asks were found undelivered (`D214`). Kept **verbatim and
unedited** for one reason: the ledger is a *reading* of this text, and a reading can drift from
its source. When an ask's wording is argued over, this is the thing to argue from.

**Do not edit, summarise, or "tidy" this file.** It is evidence, in the same way the
decision log's historical name references are.

---

i have been using the repo for sometime and there a few things i want done as a result of expriencing it and wanting improvement.
some of these will be plain out requests, some questions that depends on the answer may become requests.

is the decision log we hold in this repo somehow a tool that is also reflected in the reeve workflow ? i want certain decisions that are taken to be written internally to the project.
for example notify me everyime X happens during development, is something i asked for and it dissapears after a enough turns.
there doesnt need to be directly a decision log but something to support these statemtents.

do doc budget and allign have values to deafult to if i didnt specifclly set any ? this is critical, as if not they just dont happen.

i wodnered if we should limit the amount of tokens an agent / skill can reach before it should itself /dispatch and start a new one. 
for example sometimes i see execute agents runnint to 300-400k tokens, i wonder if their work would better if they were capped at 300k and new ones will start, the answer defintily may be no as all of the context is relevant but research would be intresting here. either way it may be worth setting a cap at something high to make sure agents dont reach it for example like 600k would be too much on matter what in my opinion, but agian research.

just a statement not a request, anything regarding org mode is currenly on hold,
soon im starting to work in a company and thne ill adjust and better understand what it requires from me.

something i want to be inheriet in the way the orchestrator and the whole repo works. i want to judge at (i want to say every turn but not really where needed) if there is work that can be done in parrelel and doing so wont hurt its integrity and qualiy then it should always be a priority to speed development up.

another thing to increase effinecy. i noticed and it makes sense that there are so many hangs, it can be while research is happening, while an exeucite is running, or something that isnt even directly the repos fault like a commit gate waiting. in all of this time again only whenever possible and it doesnt hurt the integrity and quality of the work, we should dispatch work to be done, whether its small researches that are to be needed soon, maybe its smaller executes whatever is possible to increase effinecy.

notice these 2 points need to be a part internlly of the project to work well otherwise they will just be forgetton about.

another point - sometimes i see agents returning instead of a normal size of data on their work for example 100k 150k tokens. i think we should give each skill / agent we dispatch a return format that is limited to a reasonable amount of context, and it can also save its work in a temp place that will be delted in its time ( we need to set when it will be deleted otherwise it will just grow unreasonably) to reffrence if needed.

something i did manually with everything and i think also should be an internal part of the repo.

i realized this repo is good for driving a project autonmously end to end with me being an over viewer, that doesnt allow me to dive deep into each of its parts and thats okay that is what it was built to do, ofc i will not be an expert on everything i do with it. with that being said, i noticed me doing the following thing.
setting up a goal, letting the repo drive it each time makign sure its on path and just lettig it run, reach ctx limit , dispatch, clear run .... until we reach that goal and then steer the ship again.
i want this to be something internal in the project.
whenever a goal is set it should drive to it continously (ofc i will still need to /clear we will get to that), measure its course and make sure it is always on the path to the set goal, for example if a number of sessions set out to do X but were unsucesfful with it and just kept trying at it not progressing its important that it will know to stop, understand what happened throughout and why it isnt progressing, reevuaalte research and then continue on the path to its goal.

also, i want in each chat that is driven with this repo, whenever we reach the 30-35% ctx limit for it to run dispatch and tell me to clear and continue in another chat, 
currently there is the banner which is nice, but again this is omething i want to internally be a part of the repo. with that being said i think we should also reasearch whether that 300k is a good limit. 
for an agent doing one thing i understand going to 300-500k cause its all regarding that exact same thing, but the orechstartor touches many surfaces, and as such it should have a more narrow ctx limit before dispatching. 300k may be the prfect number but also maybe it isnt worth a good research on right practice.

also i wouldve wished to have the repo when working towards one goal to do the dipstach clear continue loop autonmously without me having to run /clear and write continue in the new chat, if this is still a restraint we cant get around i accept it. but lets put some thought into it. (if it possible it is also importnat that i will be able to stop the loop to ask questions and steer but it would be a great timesaver when just letting sessions run to accomplish a goal)

overall these are the changes i seek for the next realese of this project (this plugin), lets do the research, brainstorming, and decision taking needed for this to come true.
discuss how we are going to do it, put it on a roadmap and start working towards these goals.
