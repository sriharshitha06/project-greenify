import os
import numpy as np
import joblib

class CarbonPredictor:
    def __init__(self):
        self.models_dir = os.path.join(os.path.dirname(__file__), "models")
        self.scaler = None
        self.regressor = None
        self.classifier = None
        self.anomaly_detector = None
        self.load_models()

    def load_models(self):
        try:
            self.scaler = joblib.load(os.path.join(self.models_dir, "scaler.joblib"))
            self.regressor = joblib.load(os.path.join(self.models_dir, "regressor.joblib"))
            self.classifier = joblib.load(os.path.join(self.models_dir, "classifier.joblib"))
            self.anomaly_detector = joblib.load(os.path.join(self.models_dir, "anomaly_detector.joblib"))
            print("ML models loaded successfully.")
        except Exception as e:
            print(f"Error loading ML models: {e}. Running fallback calculation.")

    def get_diet_value(self, diet_type: str) -> float:
        diet_map = {'vegan': 0.0, 'vegetarian': 1.0, 'meat_heavy': 2.0}
        return diet_map.get(diet_type.lower(), 1.0) # Default to vegetarian

    def calculate_math_fallback(self, data: dict) -> float:
        # Fallback carbon calculation based on standards
        electricity = data.get('electricity_kwh', 0.0)
        lpg = data.get('lpg_cylinders', 0.0)
        petrol = data.get('petrol_liters', 0.0)
        diesel = data.get('diesel_liters', 0.0)
        cng = data.get('cng_liters', 0.0)
        diet_type = data.get('diet_type', 'vegetarian')
        waste_recycled = data.get('waste_recycled_pct', 0.0)
        public_transport = data.get('public_transport_km', 0.0)
        
        diet_map_co2 = {'vegan': 2.0, 'vegetarian': 3.5, 'meat_heavy': 7.0}
        diet_co2 = diet_map_co2.get(diet_type.lower(), 3.5)
        waste_co2 = 1.5 * (1.0 - waste_recycled / 100.0)
        
        co2 = (
            (electricity * 0.62) +
            (lpg * 24.4) +
            (petrol * 2.35) +
            (diesel * 2.68) +
            (cng * 2.50) +
            diet_co2 +
            waste_co2 +
            (public_transport * 0.08)
        )
        return max(0.5, co2)

    def classify_fallback(self, co2: float) -> str:
        if co2 < 6.0:
            return 'Low'
        elif co2 < 16.0:
            return 'Medium'
        elif co2 < 35.0:
            return 'High'
        else:
            return 'Extreme'

    def predict(self, input_data: dict) -> tuple[float, str]:
        # If models are not loaded, use fallback
        if not all([self.scaler, self.regressor, self.classifier]):
            co2 = self.calculate_math_fallback(input_data)
            category = self.classify_fallback(co2)
            return float(co2), category

        # Extract parameters in precise training feature order:
        # 'electricity_kwh', 'lpg_cylinders', 'petrol_liters', 'diesel_liters', 
        # 'cng_liters', 'diet_type', 'waste_recycled_pct', 'public_transport_km', 
        # 'cycling_walking_km'
        features = [
            float(input_data.get('electricity_kwh', 0.0)),
            float(input_data.get('lpg_cylinders', 0.0)),
            float(input_data.get('petrol_liters', 0.0)),
            float(input_data.get('diesel_liters', 0.0)),
            float(input_data.get('cng_liters', 0.0)),
            self.get_diet_value(input_data.get('diet_type', 'vegetarian')),
            float(input_data.get('waste_recycled_pct', 0.0)),
            float(input_data.get('public_transport_km', 0.0)),
            float(input_data.get('cycling_walking_km', 0.0))
        ]
        
        try:
            # Reshape feature list for single-sample inference
            features_arr = np.array(features).reshape(1, -1)
            
            # Scale features
            features_scaled = self.scaler.transform(features_arr)
            
            # Predict regressor and classifier
            carbon_val = float(self.regressor.predict(features_scaled)[0])
            classification = str(self.classifier.predict(features_scaled)[0])
            
            # Bounds check to avoid negative emissions
            return max(0.1, carbon_val), classification
        except Exception as e:
            print(f"Prediction inference error: {e}. Reverting to fallback.")
            co2 = self.calculate_math_fallback(input_data)
            category = self.classify_fallback(co2)
            return float(co2), category

    def detect_anomaly(self, input_data: dict) -> bool:
        """
        Detects if input parameters are statistically anomalous or physically impossible
        """
        # Hard limits check (rule-based anomalies for extreme inputs that ML may miss)
        if (
            input_data.get('electricity_kwh', 0.0) > 1000.0 or
            input_data.get('lpg_cylinders', 0.0) > 5.0 or
            input_data.get('petrol_liters', 0.0) > 500.0 or
            input_data.get('diesel_liters', 0.0) > 500.0 or
            input_data.get('cng_liters', 0.0) > 200.0 or
            input_data.get('public_transport_km', 0.0) > 2000.0 or
            input_data.get('cycling_walking_km', 0.0) > 100.0
        ):
            return True

        if not self.anomaly_detector:
            return False

        try:
            features = [
                float(input_data.get('electricity_kwh', 0.0)),
                float(input_data.get('lpg_cylinders', 0.0)),
                float(input_data.get('petrol_liters', 0.0)),
                float(input_data.get('diesel_liters', 0.0)),
                float(input_data.get('cng_liters', 0.0)),
                self.get_diet_value(input_data.get('diet_type', 'vegetarian')),
                float(input_data.get('waste_recycled_pct', 0.0)),
                float(input_data.get('public_transport_km', 0.0)),
                float(input_data.get('cycling_walking_km', 0.0))
            ]
            features_arr = np.array(features).reshape(1, -1)
            
            # IsolationForest returns -1 for anomalies, 1 for normal
            prediction = self.anomaly_detector.predict(features_arr)[0]
            return prediction == -1
        except Exception as e:
            print(f"Anomaly detection model error: {e}")
            return False

# Instantiate a single global predictor
predictor = CarbonPredictor()
