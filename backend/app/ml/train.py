import os
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, IsolationForest
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score, classification_report

def generate_synthetic_data(num_samples=5000):
    np.random.seed(42)
    
    # Generate random realistic inputs
    electricity = np.random.uniform(0.0, 30.0, num_samples)     # kWh/day
    lpg = np.random.choice([0.0, 0.05, 0.1], size=num_samples, p=[0.8, 0.15, 0.05]) # average cylinders/day
    petrol = np.random.exponential(scale=3.0, size=num_samples)  # liters/day, skewed towards lower
    diesel = np.random.exponential(scale=1.5, size=num_samples)  # liters/day, skewed towards lower
    cng = np.random.exponential(scale=1.0, size=num_samples)     # kg/day
    
    diet = np.random.choice(['vegan', 'vegetarian', 'meat_heavy'], size=num_samples, p=[0.15, 0.55, 0.3])
    waste_recycled = np.random.uniform(0.0, 100.0, num_samples)  # percentage
    public_transport = np.random.exponential(scale=8.0, size=num_samples) # km/day
    cycling_walking = np.random.uniform(0.0, 15.0, num_samples)  # km/day
    
    # Map diet types to numerical values for math
    diet_map = {'vegan': 0.0, 'vegetarian': 1.0, 'meat_heavy': 2.0}
    diet_num = np.array([diet_map[d] for d in diet])
    
    # Calculate carbon footprint (target regression value) based on actual green metrics
    # electricity: 0.62 kg CO2e/kWh
    # lpg: 24.4 kg CO2e/cylinder (cylinder is typically ~14.2kg, lpg emission ~2.98kg/kg)
    # petrol: 2.35 kg CO2e/liter
    # diesel: 2.68 kg CO2e/liter
    # cng: 2.50 kg CO2e/kg
    # diet: vegan=2.0kg/day, vegetarian=3.5kg/day, meat_heavy=7.0kg/day
    # waste: standard 1.5kg/day, reduced by recycling percentage (recycled portion has 0 footprint)
    # public_transport: 0.08 kg CO2e/km
    # cycling_walking: 0 kg CO2e/km
    
    diet_co2 = np.choose(diet_num.astype(int), [2.0, 3.5, 7.0])
    waste_co2 = 1.5 * (1.0 - waste_recycled / 100.0)
    
    base_carbon = (
        (electricity * 0.62) +
        (lpg * 24.4) +
        (petrol * 2.35) +
        (diesel * 2.68) +
        (cng * 2.50) +
        diet_co2 +
        waste_co2 +
        (public_transport * 0.08)
    )
    
    # Add noise to represent unmeasured lifestyle factors
    noise = np.random.normal(0, 0.5, num_samples)
    carbon_footprint = np.clip(base_carbon + noise, 0.5, None) # Carbon footprint cannot be negative
    
    # Classification categories
    # Low: < 5.0 kg CO2e/day
    # Medium: 5.0 - 15.0 kg CO2e/day
    # High: 15.0 - 35.0 kg CO2e/day
    # Extreme: >= 35.0 kg CO2e/day
    classification = []
    for cf in carbon_footprint:
        if cf < 6.0:
            classification.append('Low')
        elif cf < 16.0:
            classification.append('Medium')
        elif cf < 35.0:
            classification.append('High')
        else:
            classification.append('Extreme')
            
    df = pd.DataFrame({
        'electricity_kwh': electricity,
        'lpg_cylinders': lpg,
        'petrol_liters': petrol,
        'diesel_liters': diesel,
        'cng_liters': cng,
        'diet_type': diet_num,
        'waste_recycled_pct': waste_recycled,
        'public_transport_km': public_transport,
        'cycling_walking_km': cycling_walking,
        'carbon_footprint': carbon_footprint,
        'classification': classification
    })
    return df

def train_and_save_models():
    print("Generating synthetic carbon dataset...")
    df = generate_synthetic_data(6000)
    
    # Features & Targets
    features = [
        'electricity_kwh', 'lpg_cylinders', 'petrol_liters', 'diesel_liters', 
        'cng_liters', 'diet_type', 'waste_recycled_pct', 'public_transport_km', 
        'cycling_walking_km'
    ]
    
    X = df[features]
    y_reg = df['carbon_footprint']
    y_clf = df['classification']
    
    # Split datasets
    X_train, X_test, y_reg_train, y_reg_test = train_test_split(X, y_reg, test_size=0.2, random_state=42)
    _, _, y_clf_train, y_clf_test = train_test_split(X, y_clf, test_size=0.2, random_state=42)
    
    # Scale numerical features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 1. Regression Model
    print("Training RandomForestRegressor...")
    regressor = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    regressor.fit(X_train_scaled, y_reg_train)
    
    # Evaluate Regressor
    reg_pred = regressor.predict(X_test_scaled)
    mse = mean_squared_error(y_reg_test, reg_pred)
    r2 = r2_score(y_reg_test, reg_pred)
    print(f"Regressor Results: MSE = {mse:.4f}, R2 = {r2:.4f}")
    
    # 2. Classification Model
    print("Training RandomForestClassifier...")
    classifier = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    classifier.fit(X_train_scaled, y_clf_train)
    
    # Evaluate Classifier
    clf_pred = classifier.predict(X_test_scaled)
    acc = accuracy_score(y_clf_test, clf_pred)
    print(f"Classifier Results: Accuracy = {acc:.4f}")
    print(classification_report(y_clf_test, clf_pred))
    
    # 3. Anomaly Detection
    # Train an IsolationForest on normal activity features to identify outliers at runtime
    print("Training IsolationForest for anomaly detection...")
    anomaly_detector = IsolationForest(contamination=0.01, random_state=42)
    anomaly_detector.fit(X_train) # Fit on raw features directly (we'll predict on raw features or scaled, fitting on raw is fine and robust)
    
    # Ensure models directory exists
    models_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(models_dir, exist_ok=True)
    
    # Save artifacts
    print(f"Saving artifacts to {models_dir}...")
    joblib.dump(scaler, os.path.join(models_dir, "scaler.joblib"))
    joblib.dump(regressor, os.path.join(models_dir, "regressor.joblib"))
    joblib.dump(classifier, os.path.join(models_dir, "classifier.joblib"))
    joblib.dump(anomaly_detector, os.path.join(models_dir, "anomaly_detector.joblib"))
    print("Models saved successfully!")

if __name__ == "__main__":
    train_and_save_models()
