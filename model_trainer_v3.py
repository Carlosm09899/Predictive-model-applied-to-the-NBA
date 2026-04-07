import pandas as pd
import xgboost as xgb
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib

def train_multi_output_model():
    print("🚀 Entrenando el Modelo Multi-Salida (Spread + Total + Moneyline)...")
    df = pd.read_csv("nba_train_set.csv")

    features = [
    'HOME_PTS_SEASON_AVG', 'HOME_PTS_EWMA', 'HOME_DEF_SEASON_AVG', 'HOME_IS_B2B', 
    'HOME_3P_PCT_EWMA', 'HOME_DEF_EFF_EWMA',
    'AWAY_PTS_SEASON_AVG', 'AWAY_PTS_EWMA', 'AWAY_DEF_SEASON_AVG', 'AWAY_IS_B2B', 
    'AWAY_3P_PCT_EWMA', 'AWAY_DEF_EFF_EWMA'
    ]
    
    # Definimos DOS targets ahora
    X = df[features]
    y = df[['HOME_PTS_ACTUAL', 'AWAY_PTS_ACTUAL']]                                                                                  

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Configuramos el regresor multi-salida con los mejores parámetros que ya encontramos
    base_xgb = xgb.XGBRegressor(
        n_estimators=100, 
        learning_rate=0.05, 
        max_depth=5, 
        subsample=0.8,
        objective='reg:squarederror'
    )
    
    model = MultiOutputRegressor(base_xgb)
    model.fit(X_train, y_train)

    # Evaluación
    preds = model.predict(X_test)
    mae_home = mean_absolute_error(y_test.iloc[:, 0], preds[:, 0])
    mae_away = mean_absolute_error(y_test.iloc[:, 1], preds[:, 1])

    print("-" * 30)
    print(f"✅ ¡Cerebro Multi-Salida listo!")
    print(f"📊 MAE Local: {mae_home:.2f} | MAE Visita: {mae_away:.2f}")
    print("-" * 30)

    joblib.dump(model, 'nba_model_v1.pkl')
    print("💾 Modelo guardado. ¡Listo para conquistar todas las apuestas!")

if __name__ == "__main__":
    train_multi_output_model()