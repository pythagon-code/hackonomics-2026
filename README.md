# EcoSphere

![Demo](images/demo.jpg)

EcoSphere is an interactive 3D visualization tool for exploring global economic data using GDP from the World Bank. It allows users to analyze country-level economic trends, compare similarity between countries, and view clustering results on a 3D globe.

## Features

- 3D globe-based visualization of countries  
- GDP-based color encoding  
- Adjustable time range for analysis  
- Log scaling for improved data interpretation  
- Similarity matching between countries using GDP growth patterns  
- Multi-country comparison with aggregated similarity scoring  
- Clustering of countries using K-Means  
- Interactive country selection  
- Dynamic updates based on user input  

## Tech Stack

- Ursina Engine (3D visualization framework)  
- Python  
- NumPy / SciPy  
- World Bank GDP dataset  

## Installation & Setup

### 1. Clone the repository
```
git clone https://github.com/pythagon-code/eco-sphere.git
cd eco-sphere
```

### 2. Create a virtual environment
```
python -m venv .venv
```

### 3. Activate the virtual environment
On Windows Powershell
```
.venv\Scripts\activate.ps1
```
On Linux/Mac terminal
```
source .venv/bin/activate
```

### 4. Install dependencies
```
pip install -r requirements.txt
```

## Running the Project
```
python main.py
```

## Future Improvements

- Add forecasting and counterfactual analysis  
- Improve clustering visualizations  
- Add filtering and search for countries  
- Expand similarity comparison tools (top-N matches, rankings)  
- Enhance UI/UX for deeper exploration  