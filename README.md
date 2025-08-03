# Pokémon Trading Card Price Prediction Using Machine Learning

With the recent surge of demand for trading cards, the market price of many Pokémon cards has absolutely skyrocketed, with many selling for thousands of dollars. This project aims to build a machine learning model that will accurately predict the price value of Pokémon cards, given its attributes. While all analysis and modeling is done in R, the raw data was collected using Python through the Pokémon TCG Developer Portal API. Machine learning models used to predict card prices are Linear Regression, KNN, Elastic Net, Random Forest, and Boosted Trees. The criteria in deciding the best performing model was comparing the average R^2 and RMSE across cross-validation folds. Through our analysis we found that boosted trees performed the best and was able to accurately identify trends in prices based on card details.

The full report of my project is detailed within "pokemontcg_ml.html"

If you would like to run the python script for yourself, you will need your own API key. Create a .env file in the project root directory with the following:

API_KEY=your_api_key_
