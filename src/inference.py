import pandas as pd
import pickle

def load_model(filepath: str):
    """Loads a trained model from disk."""
    print(f"Loading model from {filepath}...")
    with open(filepath, 'rb') as f:
        return pickle.load(f)

def run_inference(model, new_data: pd.DataFrame) -> np.ndarray:
    """Runs inference on new data."""
    print("Running inference...")
    return model.predict(new_data)

if __name__ == "__main__":
    print("Inference module.")
