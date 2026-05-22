# AI Tooling

## What I used

Claude Code — Anthropic's coding assistant running in my terminal — for the entire build. I worked in a conversational pair-programming pattern: I'd describe what I wanted the next phase to do, the assistant would propose code, I'd read it, run it, push back on the parts I didn't like or didn't understand, and we'd iterate until each piece landed correctly.

I did not use it as a code-completion tool primarily. I used it as a collaborator that
could write, explain, and debug, while I kept ownership of every design decision and validated every output by running the code myself.

## How it helped

**Scaffolding without typing fatigue.** Setting up a Python project with twelve modules, a Docker bundle, GitHub Actions, and a Streamlit UI involves a lot of mechanical work that's not interesting. Having the assistant draft the boilerplate (Dockerfile, Caddyfile, pyproject-style requirements, test
harness) freed me to focus on the parts that mattered — corpus design, the RAG pipeline shape, the eval methodology.

**Debugging real issues with a fast feedback loop.** A few examples worth
calling out:

- The Render container kept dying with "Operation not permitted" on the Caddy
  binary. The first instinct (executable bit stripped during multi-stage
  COPY) was wrong; the real cause was file capabilities baked into the
  official Caddy image. Working through this with the assistant cut the
  debug cycle from "search the web for hours" to "form a hypothesis, test it
  in five minutes, move on."

- The initial evaluation run showed 40% groundedness, which felt wrong given
  how clearly the answers matched the policy text. Working through the
  results.json together surfaced two measurement bugs (citation regex too
  bug, judge seeing truncated snippets) that I fixed quickly. Without a
  collaborator I might have accepted 40% as the real number and tried to
  "improve the model" instead of fixing the evaluation bug.

- The Streamlit duplicate-render bug when clicking sample question buttons.
  The fix (use `on_click` callbacks instead of `st.rerun()` inside a button
  block) is the kind of thing you only know if you've hit it before. Saved
  me an hour.

**Explanations on demand.** Every time we built something non-trivial, I asked the assistant to write a walkthrough doc for that phase — covering not just the code but the underlying concept (what an embedding actually is, why LLM-as-judge isn't perfect, why chunking is more important than the model
choice). I have a stack of these walkthroughs in my local docs/ folder that I'll re-read before interviews and the exam. They reinforced my understanding while the code was fresh, which is when concepts stick best.

**Honest pushback on my ideas.** A few times I suggested an approach and the assistant flagged a trade-off I hadn't considered — for example, I initially wanted to bundle everything into a single Streamlit app, and the assistant pointed out that the rubric explicitly asks for a `/chat` REST endpoint that Streamlit can't serve cleanly. We split into FastAPI + Streamlit, which turned out to be the right call for both the rubric and for any future client (mobile, Slack bot) that might consume the API.

## What didn't work well

**Over-eagerness on early actions.** Once or twice the assistant pushed changes without explicitly asking me first. I asked for "no pushes without permission" early on and after that point everything
went through a confirmation step. Worth being explicit about as a working rule.

**Latency-related hallucination.** Early in the project the assistant claimed "the whole pipeline runs in ~400ms" in a walkthrough doc. The number was lifted from Groq's marketing for generation-only latency, not from any measurement I'd done. When I pointed this out the doc was corrected, but the
incident reinforced that any number in any artifact needs to come from a measurement I ran myself, not from a generic plausible-sounding number.

**Initial groundedness claims**. The first evaluation run reported 40% groundedness, but the answers were obviously correct on inspection. The assistant initially accepted this number at face value before I pushed to investigate. It turned out to be two measurement bugs in the eval harness,
not a real model problem. Lesson: trust nothing until you've inspected the underlying data.


## Overall

AI tooling made this project measurably faster and meaningfully better. The faster part is obvious — I would not have built a Docker + Caddy + FastAPI + Streamlit + LangChain stack in the same calendar time without help. The better part is more subtle: having a knowledgeable collaborator to debate
design decisions with raises the floor on what you can ship as a solo engineer. The trade-off is that you have to stay actively engaged — read the code, run it, question it — or you end up shipping a stack you don't actually understand. For me the value of the project was the understanding, not the artifact, so I leaned into the engagement and the walkthroughs.
