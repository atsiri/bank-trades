import streamlit as st
import pandas as pd
from streamlit_agraph import agraph, Node, Edge, Config
import streamlit.components.v1 as components

# --- 1. PASSWORD PROTECTION ---
def check_password():
    """Returns True if the user had the correct password."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    # If already correct, return True
    if st.session_state["password_correct"]:
        return True

    # Show input for password
    placeholder = st.empty()
    with placeholder.container():
        st.write("## 🔒 Dashboard Login")
        password = st.text_input("Password", type="password")
        if password:
            if password == st.secrets["APP_PASSWORD"]:
                st.session_state["password_correct"] = True
                placeholder.empty() # Clear the login form
                st.rerun()
            else:
                st.error("😕 Password incorrect")
    return False

if check_password():   
    # --- Header Images ---
    # Using columns to place images at the extreme left and right
    col_img1, col_mid, col_img2 = st.columns([1, 8, 1])

    with col_img1:
        # Replace 'image1.png' with your actual file path or URL
        st.image("image1.png", width=100) 

    with col_img2:
        # Replace 'image2.png' with your actual file path or URL
        st.image("image2.png", width=100)
# ---------------------------------
   
    # --- 1. PAGE CONFIG & THEME ---
    st.set_page_config(
        layout="wide", 
        page_title="Bank Himbara Network Analysis",
        initial_sidebar_state="expanded"
    )

    # Force White Theme CSS from your reference project
    st.markdown("""
        <style>
        .stApp { background-color: #FFFFFF; }
        [data-testid="stSidebar"] {
            background-color: #F8F9FA !important;
            border-right: 1px solid #E0E0E0;
        }
        h1, h2, h3, h4, p, span, label { color: #000000 !important; }
        .stDataFrame, [data-testid="stDataFrame"] {
            background-color: #FFFFFF !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- 2. DATA LOADING ---
    @st.cache_data
    def load_data():
        # << CHANGED: Updated data source to himbara.csv >>
        network_df = pd.read_csv('data/bank.csv')
        network_df = network_df.dropna(subset=['Source', 'Target'])
        network_df['Jabatan'] = network_df['Jabatan'].fillna('')
        # << CHANGED: Added broker_trx.csv data source >>
        broker_df = pd.read_csv('data/broker_trx.csv')
        return network_df, broker_df

    raw_df, broker_trx_df = load_data()
    
    # --- 2. PREPARE FILTER LISTS ---
    bank_list = sorted(raw_df['Bank'].unique())
    broker_list = sorted(broker_trx_df['Nama Broker'].unique())
    name_list = sorted(raw_df['Source'].unique())
    # Color map for banks
    palette = ["#FF4B4B", "#1E88E5", "#4CAF50", "#FF9800", "#9C27B0", "#00BCD4", "#795548"]
    bank_color_map = {bank: palette[i % len(palette)] for i, bank in enumerate(bank_list)}

    broker_list = sorted(broker_trx_df['Nama Broker'].unique())

    #filter
    filter_css = ""
    for bank, color in bank_color_map.items():
        # Targets the multiselect labels to match node colors
        filter_css += f"""
        span[data-baseweb="tag"][aria-label*="{bank}"] {{
            background-color: {color} !important;
            color: white !important;
        }}
        """
    st.markdown(f"<style>{filter_css}</style>", unsafe_allow_html=True)

    # << CHANGED: Created registry so nodes inherit color from their affiliated bank >>
    node_color_registry = {}
    for _, row in raw_df.iterrows():
        color = bank_color_map.get(row['Bank'], "#D3D3D3")
        node_color_registry[row['Source']] = color
        node_color_registry[row['Target']] = color

    # --- 3. SIDEBAR (FILTERS) ---
    st.sidebar.header("🔍 Filter & Pencarian")

    if st.sidebar.button("🔄 Reset Dashboard"):
        for key in ["search", "banks", "jabs"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    # st.sidebar.header("🔍 Filter & Pencarian")
    search_query = st.sidebar.text_input("Cari Nama / Jabatan / Broker:", value="").upper().strip()
    selected_banks = st.sidebar.multiselect("Pilih Bank:", options=bank_list, default=bank_list)
    selected_names = st.sidebar.multiselect("Pilih Nama:", options=name_list)
    selected_brokers = st.sidebar.multiselect("Pilih Broker:", options=broker_list)

    # --- 4. FILTERING LOGIC ---
    f_graph = raw_df[raw_df['Bank'].isin(selected_banks)].copy()

    # << CHANGED: Apply Nama filter if selections are made >>
    if selected_names:
        f_graph = f_graph[f_graph['Source'].isin(selected_names)]

    # << CHANGED: Apply Broker filter if selections are made >>
    # Filters graph to show connections involving selected brokers
    if selected_brokers:
        f_graph = f_graph[(f_graph['Source'].isin(selected_brokers)) | (f_graph['Target'].isin(selected_brokers))]

    if search_query:
        mask = (f_graph['Source'].str.upper().str.contains(search_query) |
                f_graph['Target'].str.upper().str.contains(search_query) |
                f_graph['Jabatan'].str.upper().str.contains(search_query))
        f_graph = f_graph[mask]
    
    # # --- 4. FILTERING LOGIC ---
    # f_graph = raw_df[raw_df['Bank'].isin(selected_banks)].copy()

    # if search_query:
    #     mask = (f_graph['Source'].str.upper().str.contains(search_query) |
    #             f_graph['Target'].str.upper().str.contains(search_query) |
    #             f_graph['Jabatan'].str.upper().str.contains(search_query))
    #     f_graph = f_graph[mask]

    # --- 5. NETWORK PREPARATION ---
    all_nodes = pd.concat([f_graph['Source'], f_graph['Target']]).unique()
    banks_set = set(raw_df['Bank'].unique())

    nodes = []
    for node_id in all_nodes:
        is_bank = node_id in banks_set or "Bank" in str(node_id)
        is_searched = search_query and search_query in str(node_id).upper()
        is_broker = node_id in broker_list
        nodes.append(Node(
            id=node_id, 
            label=node_id, 
            size=7 if is_bank else (5 if is_broker else 3),
            color="#000000" if is_broker else node_color_registry.get(node_id, "#D3D3D3"), 
            shape="diamond" if is_bank else ("triangle" if is_broker else "dot"),
            font={'size': 10, 'color': 'black'}
        ))
        
        # nodes.append(Node(
        #     id=node_id, 
        #     label=node_id, 
        #     size=7 if is_bank else 3,
        #     color=node_color_registry.get(node_id, "#D3D3D3"), 
        #     shape="diamond" if is_bank else "dot",
        #     font={'size': 10, 'color': 'black'} # << CHANGED: Resized node text >>
        # ))
        
        # nodes.append(Node(
        #     id=node_id, 
        #     label=node_id, 
        #     size=7 if is_bank else 3,
        #     color="#FF4B4B" if is_bank else ("#FF0000" if is_searched else "#1E88E5"), 
        #     shape="diamond" if is_bank else "dot",
        #     font={'size': 18, 'color': 'black'}
        # ))

    edges = []
    for _, row in f_graph.iterrows():
        edges.append(Edge(
            source=row['Source'], 
            target=row['Target'], 
            #label=row['Jabatan'],
            width=max(1, row['Weight'] / 5),
            color="#D3D3D3"
        ))

    # --- 6. VISUALIZATION LAYOUT ---
    st.title("🛡️ Analisis Jejaring Bank Himbara")

    # Layout: Network on top, Details below (Simulating your previous project's structure)
    st.subheader("🕸️ Visualisasi Jaringan")

    config = Config(
        width="100%", 
        height=700, 
        directed=True,
        nodeHighlightBehavior=True, 
        collapsible=False,
        highlightColor="#F7A7A6",
        canvasBackgroundColor="white",
        link={'labelProperty': 'label', 'renderConfiguration': (True, 'blue')},
        physics=True, 
        # physics={
        #     'enabled': True,
        #     'solver': 'barnesHut',
        #     #'hierarchicalRepulsion': {'gravitationalConstant': -100, 'springLength': 250}
        # }
    )

    clicked_node = agraph(nodes=nodes, edges=edges, config=config)

    # --- 7. TABLES (Bottom Section) ---
    st.divider()
    # st.subheader("🏢 Detail Afiliasi & Hubungan")

    # if clicked_node:
    #     # Logic: Show all affiliated if bank is clicked, or specific connections for people
    #     if clicked_node in banks_set:
    #         display_df = raw_df[raw_df['Bank'] == clicked_node]
    #         st.info(f"Menampilkan seluruh personil yang berafiliasi dengan **{clicked_node}**")
    #     else:
    #         display_df = raw_df[(raw_df['Source'] == clicked_node) | (raw_df['Target'] == clicked_node)]
    #         st.info(f"Menampilkan koneksi untuk **{clicked_node}**")
    # else:
    #     display_df = f_graph
    #     st.caption("Menampilkan data berdasarkan filter sidebar (Klik node untuk fokus spesifik).")

    # st.dataframe(
    #     display_df[['Source', 'Target', 'Bank', 'Jabatan', 'Link', 'Weight']].drop_duplicates(),
    #     use_container_width=True,
    #     hide_index=True
    # )

    # << CHANGED: Expanded logic to handle Broker clicks vs Bank clicks >>
    if clicked_node or search_query in broker_list:
        active_node = clicked_node if clicked_node else search_query
        
        if active_node in broker_list:
            st.subheader(f"📈 Transaksi Broker: {active_node}")
            broker_data = broker_trx_df[broker_trx_df['Nama Broker'] == active_node]
            st.dataframe(broker_data, use_container_width=True, hide_index=True)
            
        elif active_node in bank_list:
            st.subheader(f"🏢 Detail Afiliasi Bank: {active_node}")
            display_df = raw_df[raw_df['Bank'] == active_node]
            #st.dataframe(display_df[['Source', 'Target', 'Bank', 'Jabatan', 'Link', 'Weight']], use_container_width=True, hide_index=True)
            st.dataframe(
                display_df[['Source', 'Target', 'Bank', 'Jabatan', 'Link', 'Weight']], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Link": st.column_config.LinkColumn(
                        "Sumber Referensi",
                        help="Klik untuk membuka link referensi asli",
                        validate=r"^https?://.+$",
                        display_text="Buka Link"
                    )
                }
            )
            
        else:
            st.subheader(f"👤 Koneksi Individu: {active_node}")
            display_df = raw_df[(raw_df['Source'] == active_node) | (raw_df['Target'] == active_node)]
            st.dataframe(
                display_df[['Source', 'Target', 'Bank', 'Jabatan', 'Link', 'Weight']], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Link": st.column_config.LinkColumn(
                        "Sumber Referensi",
                        display_text="Buka Link"
                    )
                }
            )
            #st.dataframe(display_df[['Source', 'Target', 'Bank', 'Jabatan', 'Link', 'Weight']], use_container_width=True, hide_index=True)

    else:
        st.info("💡 Klik node Bank (Diamond) untuk melihat personil, atau Broker (Triangle) untuk melihat riwayat transaksi.")