from functools import partial

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agents.supervisor.agent import route_intent
from app.workflows import nodes
from app.workflows.checkpoints import TransactionJournal
from app.workflows.state import WorkflowState


def build_graph(db: Session, checkpointer: TransactionJournal):
    graph = StateGraph(WorkflowState)
    graph.add_node("supervisor", nodes.supervise)
    graph.add_node("approval", nodes.review)
    for name, node in (
        ("context", nodes.collect_context), ("planner", nodes.plan),
        ("replanning", nodes.compare), ("scheduler", nodes.schedule), ("execution", nodes.execute),
        ("verification", nodes.verify), ("simulation", nodes.run_simulation),
    ):
        graph.add_node(name, partial(node, db=db))

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", route_intent, {"plan_goal": "context", "simulate": "simulation"})
    graph.add_edge("context", "planner")
    graph.add_conditional_edges(
        "planner", lambda state: bool(state.get("previous_run_id")), {True: "replanning", False: "scheduler"},
    )
    graph.add_edge("replanning", "scheduler")
    graph.add_edge("scheduler", "approval")
    graph.add_conditional_edges(
        "approval", lambda state: state["decision"] == "approve", {True: "execution", False: END}
    )
    graph.add_edge("execution", "verification")
    graph.add_edge("verification", END)
    graph.add_edge("simulation", END)
    return graph.compile(checkpointer=checkpointer)
