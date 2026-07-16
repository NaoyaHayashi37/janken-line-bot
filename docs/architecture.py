"""Regenerate docs/architecture.png.

Requires Graphviz and the diagrams package:

    brew install graphviz
    pip install diagrams

Then, from the repository root:

    python docs/architecture.py
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.network import APIGateway
from diagrams.onprem.client import User
from diagrams.saas.chat import Line

INK = "#374151"
LINE_GREEN = "#06C755"
AWS_ORANGE = "#FF9900"

graph_attr = {
    "bgcolor": "white",
    "pad": "0.4",
    "nodesep": "0.9",
    "ranksep": "1.6",
    "fontsize": "16",
    # 2x the 96dpi default. At 96dpi the cluster labels rasterize with their
    # tops shaved off; this also gives a crisp image on HiDPI screens.
    "dpi": "192",
}
node_attr = {"fontsize": "14", "fontcolor": INK}
edge_attr = {"fontsize": "13", "fontcolor": INK, "color": "#6B7280"}

# "rank": "same" puts a cluster's nodes in a single column, so they stack
# vertically even though the graph as a whole flows left to right.
line_attr = {
    "rank": "same",
    "bgcolor": "#E8F8EE",
    "pencolor": LINE_GREEN,
    "fontcolor": "#04A648",
    "margin": "16",
}
aws_attr = {
    "rank": "same",
    "bgcolor": "#FFF4E5",
    "pencolor": AWS_ORANGE,
    "fontcolor": "#B36B00",
    "margin": "16",
}

with Diagram(
    "",
    filename="docs/architecture",
    outformat="png",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
):
    user = User("User")

    with Cluster("LINE", graph_attr=line_attr):
        msg_api = Line("Messaging API")
        line_app = Line("LINE App")
        # A label on a same-rank edge is dropped, so these use xlabel. Graphviz
        # butts an xlabel right up against the edge; the trailing spaces pad it
        # away from the arrow.
        line_app >> Edge(xlabel="Event   ", constraint="false") >> msg_api

    with Cluster("AWS", graph_attr=aws_attr):
        apigw = APIGateway("API Gateway")
        lam = Lambda("Lambda")
        apigw >> Edge(xlabel="Invoke   ", constraint="false") >> lam

    user >> Edge(label="Message", forward=True, reverse=True) >> line_app
    # The heavy weights keep each pair level, which in turn holds the two
    # clusters the same size and aligned, and leaves both edges horizontal.
    msg_api >> Edge(label="Webhook", weight="100") >> apigw
    lam >> Edge(label="Reply API", weight="100") >> line_app
