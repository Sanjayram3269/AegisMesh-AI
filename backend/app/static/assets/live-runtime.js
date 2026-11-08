"use strict";
(() => {
  const stages = [
    {
      id: "intent",
      name: "Intent",
      title: "Intent intelligence",
      glyph: "◈",
      kind: "LLM planner",
      authority: "Proposal only",
      description:
        "Interprets the request and proposes a supported action. It cannot grant permission.",
    },
    {
      id: "identity",
      name: "Identity",
      title: "Identity verification",
      glyph: "⌘",
      kind: "Deterministic control",
      authority: "Server-derived identity",
      description:
        "Verifies the authenticated session and account role. Claims inside a prompt never grant access.",
    },
    {
      id: "policy",
      name: "Policy",
      title: "Policy intelligence",
      glyph: "▱",
      kind: "Deterministic control",
      authority: "Versioned company rules",
      description:
        "Retrieves applicable passages and checks the actual tool, fields and destination against company rules.",
    },
    {
      id: "risk",
      name: "Risk",
      title: "Risk assessment",
      glyph: "◇",
      kind: "Deterministic rubric",
      authority: "Decision support",
      description:
        "Scores the proposed operation against an explicit risk rubric. High-impact work needs human review.",
    },
    {
      id: "execution",
      name: "Execution",
      title: "Execution gateway",
      glyph: "⬡",
      kind: "Protected business executor",
      authority: "Exact-action authorization",
      description:
        "Checks single-use approval, binds the exact operation and verifies its signed execution ticket.",
    },
    {
      id: "audit",
      name: "Audit",
      title: "Audit & verification",
      glyph: "⏣",
      kind: "Transactional evidence",
      authority: "Observed outcomes",
      description:
        "Records the execution receipt and audit link in the same transaction as the business operation.",
    },
  ];
  window.AegisStages = stages;
  const stateNames = {
    idle: "STANDBY",
    running: "PROCESSING",
    complete: "COMPLETE",
    waiting: "AWAITING HUMAN",
    blocked: "BLOCKED",
    error: "FAILED",
  };
  let selected = 0,
    states = {},
    observations = {},
    current = null,
    recorded = [],
    seen = 0,
    replayGeneration = 0;
  const $ = (id) => document.getElementById(id);
  const node = (tag, text, cls) => {
    const e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  };
  function dispatch(name, detail) {
    window.dispatchEvent(new CustomEvent(name, { detail }));
  }
  function inspector() {
    const stage = stages[selected],
      state = states[stage.id] || "idle";
    $("agentName").textContent = stage.title;
    $("agentGlyph").textContent = stage.glyph;
    $("agentIndex").textContent =
      `AGENT / ${String(selected + 1).padStart(2, "0")}`;
    $("agentKind").textContent = stage.kind;
    $("agentAuthority").textContent = stage.authority;
    $("agentDescription").textContent = stage.description;
    $("selectedState").textContent = stateNames[state];
    $("selectedState").dataset.state = state;
    $("agentObservation").textContent =
      observations[stage.id] ||
      "No event observed for this stage in the selected run.";
    document
      .querySelectorAll(".stage-button,.scene-label")
      .forEach((button) => {
        const id = button.dataset.stage;
        button.classList.toggle("selected", id === stage.id);
        button.dataset.state = states[id] || "idle";
        if (button.classList.contains("stage-button")) {
          button.setAttribute("aria-pressed", String(id === stage.id));
          button.querySelector(".stage-state").textContent =
            stateNames[states[id] || "idle"];
        }
      });
  }
  let followActive = true;
  function select(index, automatic = false) {
    if (!automatic) followActive = false;
    selected = index;
    inspector();
    dispatch("aegis:select-agent", { index, id: stages[index].id });
  }
  stages.forEach((stage, index) => {
    const button = node(
      "button",
      undefined,
      "stage-button" + (index === 0 ? " selected" : ""),
    );
    button.type = "button";
    button.dataset.stage = stage.id;
    button.setAttribute("aria-label", "Inspect " + stage.title);
    const name = node("span");
    name.append(
      node("span", stage.name, "stage-name"),
      node("span", "STANDBY", "stage-state"),
    );
    button.append(
      node("span", String(index + 1).padStart(2, "0"), "stage-number"),
      name,
      node("i", undefined, "stage-dot"),
    );
    button.onclick = () => select(index);
    $("agentStrip").append(button);
  });
  window.AegisSelectAgent = select;
  function showEvent(event, replay = false) {
    if (event.stage === "run") {
      if (event.state === "error")
        $("traceSummary").textContent =
          "Request failed · inspect the returned error";
      return;
    }
    states[event.stage] = event.state;
    observations[event.stage] = event.message;
    if (followActive && event.state === "running")
      select(
        stages.findIndex((stage) => stage.id === event.stage),
        true,
      );
    const item = node("div", undefined, "event-row");
    item.append(
      node("time", `${event.elapsed_ms.toFixed(1)} ms`),
      node("strong", event.stage.toUpperCase()),
    );
    const description = node("p", event.message);
    item.append(description);
    $("eventStream").append(item);
    dispatch("aegis:stage", { ...event, replay });
    inspector();
  }
  function showEvents(run) {
    if (!current || run.id !== current.id) return;
    const events = run.events.slice(seen);
    if (events.length && seen === 0) $("eventStream").replaceChildren();
    for (const event of events) {
      recorded.push(event);
      showEvent(event);
    }
    seen = run.events.length;
    if (run.complete) {
      current.done = true;
      $("runtimeMode").className = "live-state";
      $("runtimeMode").lastChild.textContent = " TRACE COMPLETE";
      $("traceSummary").textContent = run.events.some(
        (e) => e.stage === "run" && e.state === "error",
      )
        ? "Request failed · inspect the response"
        : run.operation === "execute"
          ? "Request finished · inspect the execution receipt"
          : run.operation === "review"
            ? "Review recorded · business operation has not executed"
            : "Proposal ready · no business operation executed";
      $("traceTiming").textContent =
        `${run.events.length} SERVER EVENTS · ${run.events.at(-1)?.elapsed_ms.toFixed(1) || 0} MS`;
      $("replayTrace").disabled = !recorded.length;
      dispatch("aegis:run-end", { id: run.id });
    }
  }
  function reset(run) {
    followActive = true;
    replayGeneration++;
    current = { ...run, done: false };
    recorded = [];
    seen = 0;
    states = {};
    observations = {};
    $("eventStream").replaceChildren();
    $("runtimeMode").className = "live-state active";
    $("runtimeMode").lastChild.textContent = " LIVE REQUEST";
    $("traceSummary").textContent =
      `${run.operation === "chat" ? "Planner request" : run.operation === "execute" ? "Protected execution" : run.operation === "review" ? "Manager review" : "Action proposal"} in progress`;
    $("traceTiming").textContent = "AUTHENTICATED SERVER TELEMETRY";
    $("replayTrace").disabled = true;
    dispatch("aegis:run-start", { id: run.id });
    inspector();
  }
  window.AegisLive = {
    async begin(path, auth) {
      const operation =
        path === "/chat"
          ? "chat"
          : path === "/proposals"
            ? "propose"
            : path === "/execute"
              ? "execute"
              : /^\/approvals\/.+\/review$/.test(path)
                ? "review"
                : null;
      if (!operation) return null;
      try {
        const response = await fetch("/api/ops/runs", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer " + auth,
          },
          body: JSON.stringify({ operation }),
        });
        if (!response.ok) return null;
        const run = await response.json();
        reset(run);
        let stopped = false;
        const read = async () => {
          try {
            const r = await fetch(
              "/api/ops/runs/" + encodeURIComponent(run.id),
              { headers: { Authorization: "Bearer " + auth } },
            );
            if (r.ok) {
              const data = await r.json();
              showEvents(data);
              if (data.complete) stopped = true;
            } else stopped = true;
          } catch {
            stopped = true;
          }
        };
        const poll = async () => {
          for (let attempt = 0; attempt < 160 && !stopped; attempt++) {
            await new Promise((r) => setTimeout(r, 220));
            if (!stopped) await read();
          }
        };
        poll();
        return {
          id: run.id,
          async finish() {
            await read();
            stopped = true;
            if (current?.id === run.id && !current.done) {
              $("runtimeMode").className = "live-state";
              $("runtimeMode").lastChild.textContent = " TRANSPORT ENDED";
              $("traceSummary").textContent =
                "No completion event received. Inspect the response.";
              dispatch("aegis:run-end", { id: run.id });
            }
          },
        };
      } catch {
        return null;
      }
    },
  };
  $("replayTrace").onclick = async () => {
    if (!recorded.length) return;
    const generation = ++replayGeneration;
    states = {};
    observations = {};
    inspector();
    $("runtimeMode").className = "live-state playback";
    $("runtimeMode").lastChild.textContent = " TRACE PLAYBACK";
    $("traceSummary").textContent =
      "Replaying recorded server events · no new execution";
    $("eventStream").replaceChildren();
    dispatch("aegis:run-start", { replay: true });
    for (const event of recorded) {
      if (generation !== replayGeneration) return;
      showEvent(event, true);
      await new Promise((r) => setTimeout(r, 350));
    }
    if (generation === replayGeneration) {
      $("runtimeMode").className = "live-state";
      $("runtimeMode").lastChild.textContent = " PLAYBACK COMPLETE";
      $("traceSummary").textContent =
        "Recorded trace replayed. No business action was executed.";
      dispatch("aegis:run-end", { replay: true });
    }
  };
  $("showEventLog").onclick = () => $("eventsDialog").showModal();
  $("closeEvents").onclick = () => $("eventsDialog").close();
  const headings = {
    overview: [
      "Agent overview",
      "Autonomy, under control.",
      "An intelligent workforce. An explicit execution boundary. Complete visibility.",
    ],
    assistant: [
      "AI workspace",
      "Intelligence that gets work done.",
      "One request. An inspectable plan. A result you can verify.",
    ],
    approvals: [
      "Approval queue",
      "Human judgment. Exact authority.",
      "Review sensitive work without losing sight of its scope or consequences.",
    ],
    activity: [
      "Execution ledger",
      "Every outcome, accounted for.",
      "Inspect what was requested, what was authorized and what actually changed.",
    ],
    policies: [
      "Policy registry",
      "The rules behind every decision.",
      "A visible policy contract between your organization and its AI operations.",
    ],
    checks: [
      "Adversarial lab",
      "Trust is earned at the boundary.",
      "Challenge the execution controls with observable, reproducible checks.",
    ],
  };
  window.addEventListener("aegis:view", (event) => {
    const name = event.detail,
      copy = headings[name] || headings.overview;
    $("currentPage").textContent = copy[0];
    $("pageTitle").textContent = copy[1];
    $("pageSubtitle").textContent = copy[2];
    const fleet = $("fleetPanel");
    (name === "assistant" ? $("assistantFleet") : $("fleetHome")).append(fleet);
    fleet.classList.toggle(
      "compact",
      !["overview", "assistant"].includes(name),
    );
    if ($("commandDialog").open) $("commandDialog").close();
    dispatch("aegis:resize", {});
  });
  window.addEventListener("aegis:workspace", (event) => {
    const data = event.detail;
    const target = $("recentOperations");
    target.replaceChildren();
    if (!data.receipts.length) {
      const tr = node("tr"),
        td = node(
          "td",
          "No operations yet. Start a workflow to create your first verified result.",
          "empty",
        );
      td.colSpan = 4;
      tr.append(td);
      target.append(tr);
    }
    for (const receipt of data.receipts.slice(0, 5)) {
      const row = node("tr"),
        operation = node("td");
      operation.append(
        node(
          "strong",
          receipt.action.tool
            .replace("tickets.", "Ticket · ")
            .replace("reports.", "Report · "),
        ),
        node("small", receipt.id),
      );
      const decision = node("td");
      decision.append(
        node(
          "span",
          receipt.decision.replaceAll("_", " "),
          "badge " +
            (receipt.decision === "DENY"
              ? "deny"
              : receipt.decision === "REQUIRE_APPROVAL"
                ? "pending"
                : ""),
        ),
      );
      row.append(
        operation,
        decision,
        node(
          "td",
          receipt.verified
            ? "Verified"
            : receipt.executed
              ? "Unverified"
              : "Not executed",
        ),
        node("td", receipt.gateway_latency_ms + " ms"),
      );
      target.append(row);
    }
  });
  $("commandTrigger").onclick = () => $("commandDialog").showModal();
  $("closeCommands").onclick = () => $("commandDialog").close();
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      $("commandDialog").open
        ? $("commandDialog").close()
        : $("commandDialog").showModal();
    }
  });
  document.querySelector(".org-switch").onclick = () =>
    window.AegisConsole?.view("assistant");
  inspector();
})();
