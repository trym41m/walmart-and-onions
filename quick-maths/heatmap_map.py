import pandas as pd
import os
import pgeocode
import plotly.graph_objects as go

FILEPATH = os.environ['WALMART_ONIONS_FILEPATH']

def map_to_geo(zip_code, nominatim):
	return nominatim.query_postal_code(zip_code).state_code

def main():
	nominatim = pgeocode.Nominatim('US')
	df = pd.read_json(FILEPATH ,lines=True)
	df = df.assign(state_code=lambda x: (map_to_geo(x.postal_code.astype(str), nominatim)))

	print(df)

	colorscale = ["#f7fbff", "#ebf3fb", "#deebf7", "#d2e3f3", "#c6dbef", "#b3d2e9", "#9ecae1",
	    "#85bcdb", "#6baed6", "#57a0ce", "#4292c6", "#3082be", "#2171b5", "#1361a9",
	    "#08519c", "#0b4083", "#08306b"
	]

	df_t = df.groupby('state_code')['price'].aggregate('mean').to_frame()

	df_t.reset_index(inplace=True)

	fig = go.Figure(data=go.Choropleth(
	    locations=df_t['state_code'], # Spatial coordinates
	    z = df_t['price'].astype(float), # Data to be color-coded
	    locationmode = 'USA-states', # set of locations match entries in `locations`
	    colorscale = colorscale,
	    colorbar_title = "Onion Unit Price",
	))

	fig.update_layout(
	    title_text = 'Walmart Onion Prices',
	    geo_scope='usa', # limite map scope to USA
	)

	fig.show()


if __name__ == '__main__':
	main()