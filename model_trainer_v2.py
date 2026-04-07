import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error
import joblib

def train_optimized_model():
    print("🚀 Cargando datos para el entrenamiento de élite...")
    df = pd.read_csv("nba_train_set.csv")

    # 1. Definir variables (Las mismas 12 de nuestro plan maestro)
    features = [
        'HOME_SEASON_AVG', 'HOME_EWMA', 'HOME_DEF_AVG', 'HOME_B2B', 
        'HOME_3P_PCT_EWMA', 'HOME_DEF_EFF_EWMA',
        'AWAY_SEASON_AVG', 'AWAY_EWMA', 'AWAY_DEF_AVG', 'AWAY_B2B', 
        'AWAY_3P_PCT_EWMA', 'AWAY_DEF_EFF_EWMA'
    ]
    
    X = df[features]
    y = df['TOTAL_PTS']

    # 2. División de datos
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("⚙️ Iniciando búsqueda de hiperparámetros (Tuning)...")
    
    # 3. Configuración de XGBoost y búsqueda de los mejores parámetros
    xgb_model = xgb.XGBRegressor(objective='reg:squarederror', random_state=42)
    
    param_grid = {
        'n_estimators': [100, 200],
        'max_depth': [3, 5, 7],
        'learning_rate': [0.01, 0.05, 0.1],
        'subsample': [0.8, 1.0]
    }

    grid_search = GridSearchCV(
        estimator=xgb_model,
        param_grid=param_grid,
        cv=3,
        scoring='neg_mean_absolute_error',
        verbose=1
    )

    grid_search.fit(X_train, y_train)
    
    # El mejor modelo encontrado
    best_model = grid_search.best_estimator_
    
    # 4. Evaluación
    predictions = best_model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    
    # Matemática del error
    # $$MAE = \frac{1}{n}\sum_{i=1}^{n}|y_i - \hat{y}_i|$$

    print("-" * 30)
    print(f"✅ ¡Entrenamiento completado!")
    print(f"📊 Nuevo MAE con XGBoost: {mae:.22} puntos")
    print(f"🏆 Mejores parámetros: {grid_search.best_params_}")
    print("-" * 30)

    # 5. Guardar el nuevo cerebro
    joblib.dump(best_model, 'nba_model_v1.pkl')
    print("💾 Modelo XGBoost guardado sobre el anterior.")

if __name__ == "__main__":
    train_optimized_model()