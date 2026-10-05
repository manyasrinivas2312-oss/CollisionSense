import random
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="CollisionSense",
    page_icon="📡",
    layout="wide"
)

# ============================================================
# SAME PACKET-ARRIVAL PATTERN FOR BOTH METHODS
# ============================================================

def make_arrivals(nodes, slots, probability, seed):
    rng = random.Random(seed)
    return [
        [rng.random() < probability for _ in range(nodes)]
        for _ in range(slots)
    ]


# ============================================================
# EXISTING SYSTEM: PURE ALOHA
# ============================================================

def pure_aloha(arrivals, nodes, slots, seed):
    """
    Discrete-time simulation model of Pure ALOHA.

    A ready node transmits immediately.
    If more than one node transmits in the same time unit,
    a collision occurs. Collided packets wait for an independent
    random delay and then retransmit.
    """

    rng = random.Random(seed + 1000003)

    schedule = {}
    scheduled_nodes = set()

    attempts = 0
    successful = 0
    collision_events = 0
    collided_attempts = 0
    total_wait = 0
    wait_count = 0

    for t in range(slots):

        tx = list(schedule.pop(t, []))

        for node in tx:
            scheduled_nodes.discard(node)

        # New packets transmit immediately when their node is free.
        for node in range(nodes):
            if (
                node not in scheduled_nodes
                and node not in tx
                and arrivals[t][node]
            ):
                tx.append(node)

        if not tx:
            continue

        attempts += len(tx)

        # One transmitter = successful transmission.
        if len(tx) == 1:
            successful += 1

        # More than one transmitter = collision.
        else:
            collision_events += 1
            collided_attempts += len(tx)

            for node in tx:
                backoff = rng.randint(1, 5)

                schedule.setdefault(
                    t + backoff, []
                ).append(node)

                scheduled_nodes.add(node)

                total_wait += backoff
                wait_count += 1

    collision_rate = (
        collided_attempts / attempts
        if attempts else 0.0
    )

    throughput = successful / slots

    average_waiting_time = (
        total_wait / wait_count
        if wait_count else 0.0
    )

    return {
        "attempts": attempts,
        "successful": successful,
        "collision_events": collision_events,
        "collided_attempts": collided_attempts,
        "collision_rate": collision_rate,
        "throughput": throughput,
        "waiting_time": average_waiting_time
    }


# ============================================================
# PROPOSED SYSTEM: COLLISION SEPARATION WINDOW (CSW)
# ============================================================

def csw(arrivals, nodes, slots, seed):
    """
    Proposed Collision Separation Window (CSW).

    After a collision:
    1. Identify all collided nodes.
    2. Give each collided node a different future retry slot.
    3. Reserve those retry slots.
    4. New packets cannot use a reserved retry slot.

    This is the specific modification being compared with
    the Pure ALOHA baseline.
    """

    schedule = {}
    reserved = {}
    scheduled_nodes = set()

    attempts = 0
    successful = 0
    collision_events = 0
    collided_attempts = 0
    total_wait = 0
    wait_count = 0

    for t in range(slots):

        tx = list(schedule.pop(t, []))

        # Remember reservation status BEFORE removing it.
        slot_was_reserved = t in reserved

        for node in tx:
            scheduled_nodes.discard(node)

        reserved.pop(t, None)

        # New packets cannot contend in a reserved retry slot.
        if not slot_was_reserved:

            for node in range(nodes):

                if (
                    node not in scheduled_nodes
                    and node not in tx
                    and arrivals[t][node]
                ):
                    tx.append(node)

        if not tx:
            continue

        attempts += len(tx)

        # One transmitter = success.
        if len(tx) == 1:
            successful += 1

        # More than one transmitter = collision.
        else:
            collision_events += 1
            collided_attempts += len(tx)

            number_of_collided_nodes = len(tx)

            # Find different future retry slots.
            retry_slots = []
            candidate = t + 1

            while (
                len(retry_slots) < number_of_collided_nodes
                and candidate < slots
            ):

                if (
                    candidate not in reserved
                    and candidate not in schedule
                ):
                    retry_slots.append(candidate)

                candidate += 1

            # Assign one different retry slot to each collided node.
            for node, retry_slot in zip(
                tx, retry_slots
            ):

                reserved[retry_slot] = node

                schedule.setdefault(
                    retry_slot, []
                ).append(node)

                scheduled_nodes.add(node)

                total_wait += retry_slot - t
                wait_count += 1

    collision_rate = (
        collided_attempts / attempts
        if attempts else 0.0
    )

    throughput = successful / slots

    average_waiting_time = (
        total_wait / wait_count
        if wait_count else 0.0
    )

    return {
        "attempts": attempts,
        "successful": successful,
        "collision_events": collision_events,
        "collided_attempts": collided_attempts,
        "collision_rate": collision_rate,
        "throughput": throughput,
        "waiting_time": average_waiting_time
    }


def run_pair(nodes, slots, probability, seed):

    arrivals = make_arrivals(
        nodes,
        slots,
        probability,
        seed
    )

    pure = pure_aloha(
        arrivals,
        nodes,
        slots,
        seed
    )

    proposed = csw(
        arrivals,
        nodes,
        slots,
        seed
    )

    return pure, proposed


def percentage_reduction(old_value, new_value):

    if old_value == 0:
        return 0.0

    return (
        (old_value - new_value)
        / old_value
    ) * 100


# ============================================================
# DASHBOARD
# ============================================================

st.title("📡 CollisionSense")

st.subheader(
    "MAC Collision Behaviour Analysis and Improvement Simulator"
)

st.write(
    """
    CollisionSense analyses collision behaviour in Pure ALOHA and
    compares it with the proposed Collision Separation Window (CSW).
    """
)

st.divider()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("⚙️ Simulation Controls")

nodes = st.sidebar.number_input(
    "Number of Nodes",
    min_value=2,
    max_value=100,
    value=10,
    step=1
)

slots = st.sidebar.number_input(
    "Number of Time Units",
    min_value=1000,
    max_value=20000,
    value=5000,
    step=500
)

probability = st.sidebar.slider(
    "Packet Probability",
    min_value=0.001,
    max_value=0.10,
    value=0.020,
    step=0.001
)

seed = st.sidebar.number_input(
    "Random Seed",
    min_value=0,
    max_value=10000,
    value=42,
    step=1
)

run = st.sidebar.button(
    "▶ Run Simulation",
    use_container_width=True
)


# ============================================================
# PROJECT INFORMATION
# ============================================================

st.header("📘 Project Overview")

st.write(
    """
    **Existing System:** Pure ALOHA

    **Problem:** After a collision, independent random
    retransmission can cause another collision.

    **Proposed Improvement:** Collision Separation Window (CSW)

    **Main idea:** Collided nodes receive different future retry
    opportunities, and those retry opportunities are reserved from
    new transmissions.
    """
)

st.header("Existing System — Pure ALOHA")

st.info(
    """
    A node transmits when it has a packet. If more than one node
    transmits during the same transmission opportunity, a collision
    occurs. The collided packets wait for a random delay and retry.
    """
)

st.header("Proposed Improvement — Collision Separation Window")

st.success(
    """
    After a collision, CSW assigns the collided nodes different
    future retry opportunities. Those retry opportunities are
    reserved so that new packets do not use them.
    """
)


# ============================================================
# RUN
# ============================================================

if run:

    with st.spinner(
        "Running Pure ALOHA and CSW..."
    ):

        pure, proposed = run_pair(
            int(nodes),
            int(slots),
            float(probability),
            int(seed)
        )

    collision_reduction = percentage_reduction(
        pure["collision_rate"],
        proposed["collision_rate"]
    )

    throughput_change = percentage_reduction(
        pure["throughput"],
        proposed["throughput"]
    )

    st.divider()
    st.header("📊 Simulation Results")


    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Pure ALOHA Collision Rate",
        f"{pure['collision_rate']:.4f}"
    )

    c2.metric(
        "CSW Collision Rate",
        f"{proposed['collision_rate']:.4f}"
    )

    c3.metric(
        "Pure ALOHA Throughput",
        f"{pure['throughput']:.4f}"
    )

    c4.metric(
        "CSW Throughput",
        f"{proposed['throughput']:.4f}"
    )


    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Pure ALOHA Waiting Time",
        f"{pure['waiting_time']:.2f}"
    )

    c2.metric(
        "CSW Waiting Time",
        f"{proposed['waiting_time']:.2f}"
    )

    c3.metric(
        "Pure ALOHA Collisions",
        f"{pure['collision_events']}"
    )

    c4.metric(
        "CSW Collisions",
        f"{proposed['collision_events']}"
    )


    # --------------------------------------------------------
    # TABLE
    # --------------------------------------------------------

    st.header("📋 Pure ALOHA vs CSW Comparison")

    comparison = pd.DataFrame({

        "Metric": [
            "Transmission Attempts",
            "Successful Transmissions",
            "Collision Events",
            "Transmission Attempts Involved in Collision",
            "Collision Rate",
            "Throughput",
            "Average Waiting Time"
        ],

        "Pure ALOHA": [
            pure["attempts"],
            pure["successful"],
            pure["collision_events"],
            pure["collided_attempts"],
            round(pure["collision_rate"], 4),
            round(pure["throughput"], 4),
            round(pure["waiting_time"], 2)
        ],

        "CSW": [
            proposed["attempts"],
            proposed["successful"],
            proposed["collision_events"],
            proposed["collided_attempts"],
            round(proposed["collision_rate"], 4),
            round(proposed["throughput"], 4),
            round(proposed["waiting_time"], 2)
        ]
    })

    st.dataframe(
        comparison,
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------------------------
    # GRAPH DATA
    # --------------------------------------------------------

    graph_data = pd.DataFrame({

        "Method": [
            "Pure ALOHA",
            "CSW"
        ],

        "Collision Rate": [
            pure["collision_rate"],
            proposed["collision_rate"]
        ],

        "Throughput": [
            pure["throughput"],
            proposed["throughput"]
        ],

        "Waiting Time": [
            pure["waiting_time"],
            proposed["waiting_time"]
        ]
    })


    # --------------------------------------------------------
    # COLLISION GRAPH
    # --------------------------------------------------------

    st.header("📈 Collision Rate Comparison")

    fig1 = px.line(
        graph_data,
        x="Method",
        y="Collision Rate",
        markers=True,
        text="Collision Rate",
        title="Pure ALOHA vs CSW — Collision Rate"
    )

    fig1.update_traces(
        texttemplate="%{y:.4f}",
        textposition="top center"
    )

    fig1.update_layout(
        height=430,
        xaxis_title="Method",
        yaxis_title="Collision Rate"
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )


    # --------------------------------------------------------
    # THROUGHPUT GRAPH
    # --------------------------------------------------------

    st.header("📈 Throughput Comparison")

    fig2 = px.line(
        graph_data,
        x="Method",
        y="Throughput",
        markers=True,
        text="Throughput",
        title="Pure ALOHA vs CSW — Throughput"
    )

    fig2.update_traces(
        texttemplate="%{y:.4f}",
        textposition="top center"
    )

    fig2.update_layout(
        height=430,
        xaxis_title="Method",
        yaxis_title="Throughput"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )


    # --------------------------------------------------------
    # WAITING TIME GRAPH
    # --------------------------------------------------------

    st.header("📈 Waiting Time Comparison")

    fig3 = px.line(
        graph_data,
        x="Method",
        y="Waiting Time",
        markers=True,
        text="Waiting Time",
        title="Pure ALOHA vs CSW — Average Waiting Time"
    )

    fig3.update_traces(
        texttemplate="%{y:.2f}",
        textposition="top center"
    )

    fig3.update_layout(
        height=430,
        xaxis_title="Method",
        yaxis_title="Average Waiting Time"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )


    # --------------------------------------------------------
    # IMPROVEMENT
    # --------------------------------------------------------

    st.divider()

    st.header("📉 Improvement")

    c1, c2 = st.columns(2)

    c1.metric(
        "Collision-Rate Reduction",
        f"{collision_reduction:.2f}%"
    )

    c2.metric(
        "Throughput Improvement",
        f"{throughput_change:.2f}%"
    )


    if collision_reduction > 0:

        st.success(
            f"""
            Under the selected conditions, CSW reduced the measured
            collision rate by **{collision_reduction:.2f}%** compared
            with Pure ALOHA.
            """
        )

    else:

        st.warning(
            """
            CSW did not reduce the measured collision rate under
            these conditions. Do not manually change the result.
            """
        )


    # --------------------------------------------------------
    # PARAMETERS
    # --------------------------------------------------------

    st.header("⚙️ Parameters Used")

    parameters = pd.DataFrame({

        "Parameter": [
            "Number of Nodes",
            "Number of Time Units",
            "Packet Probability",
            "Random Seed"
        ],

        "Value": [
            nodes,
            slots,
            probability,
            seed
        ]
    })

    st.dataframe(
        parameters,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        """
        Set the parameters on the left and click
        **▶ Run Simulation** to view the results.
        """
    )


st.divider()

st.caption(
    "CollisionSense | Computer Networks Mini Project"
)