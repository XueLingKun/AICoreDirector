class StateManager:
    def __init__(self):
        self._session_preferred_models = {}

    def set_preferred_model_index(self, session_id, index):
        self._session_preferred_models[session_id] = index
        print(f"[StateManager] Set preferred model for session {session_id} to index {index}", flush=True)

    def get_preferred_model_index(self, session_id):
        return self._session_preferred_models.get(session_id)

state_manager = StateManager() 