import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import googlemaps
from datetime import datetime
import time
import pytz

# Utility functions
@st.cache_data(ttl=3600)
def get_coordinates(address):
    try:
        geocode_result = gmaps.geocode(address)
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            return location['lat'], location['lng']
    except Exception as e:
        st.error(f"Error getting coordinates: {str(e)}")
    return None, None

@st.cache_data(ttl=3600)
def get_nearby_food_places(lat, lng, radius):
    food_types = ['restaurant', 'cafe', 'bakery', 'bar', 'meal_takeaway', 'meal_delivery']
    places = []
    for food_type in food_types:
        try:
            results = gmaps.places_nearby(location=(lat, lng), radius=radius, type=food_type)
            places.extend(results.get('results', []))
            time.sleep(0.2)  # Add a small delay to avoid hitting API rate limits
        except Exception as e:
            st.error(f"Error fetching {food_type} places: {str(e)}")
    return places

@st.cache_data(ttl=3600)
def get_place_details(place_id):
    try:
        details = gmaps.place(place_id=place_id, fields=['name', 'rating', 'formatted_phone_number', 'opening_hours', 'price_level', 'type', 'website', 'formatted_address', 'reviews', 'user_ratings_total'])
        return details.get('result', {})
    except Exception as e:
        st.error(f"Error fetching place details: {str(e)}")
        return {}

def create_map(lat, lng, places):
    m = folium.Map(location=[lat, lng], zoom_start=16, tiles="CartoDB positron")
    folium.Marker([lat, lng], popup="Your Location", icon=folium.Icon(color="red", icon="user", prefix='fa', icon_size=(32, 32))).add_to(m)
    for place in places:
        place_lat, place_lng = place['geometry']['location']['lat'], place['geometry']['location']['lng']
        folium.Marker([place_lat, place_lng], popup=place['name'], icon=folium.Icon(color="green", icon="utensils", prefix='fa')).add_to(m)
    return m

@st.cache_data(ttl=3600)
def calculate_distance(origin, destination):
    try:
        result = gmaps.distance_matrix(origin, destination, mode="walking")
        if result['status'] == 'OK':
            return result['rows'][0]['elements'][0]['distance']['text']
    except Exception as e:
        st.error(f"Error calculating distance: {str(e)}")
    return "N/A"

def is_open_now(opening_hours):
    if not opening_hours or 'periods' not in opening_hours:
        return "Unknown"
    singapore_tz = pytz.timezone('Asia/Singapore')
    current_time = datetime.now(singapore_tz)
    current_day, current_minutes = current_time.weekday(), current_time.hour * 60 + current_time.minute
    for period in opening_hours['periods']:
        if period['open']['day'] == current_day:
            open_time = int(period['open']['time'][:2]) * 60 + int(period['open']['time'][2:])
            # Check if 'close' key exists
            if 'close' in period:
                close_time = int(period['close']['time'][:2]) * 60 + int(period['close']['time'][2:])
                if open_time <= current_minutes < close_time:
                    return "Open"
            else:
                # If no 'close' time, assume it's open if current time is past opening time
                if current_minutes >= open_time:
                    return "Open"
    return "Closed"

@st.cache_resource
def get_gmaps_client():
    return googlemaps.Client(key=st.secrets["GOOGLE_MAPS_API_KEY"])

# Main application
def main():
    st.set_page_config(page_title="Food Dining Options Nearby", layout="wide")
    
    st.markdown("""
        <style>
        .reportview-container { background: #f0f4f8; }
        .main { color: #1f2937; }
        .stButton>button { background-color: #8ed1fc; color: #1f2937; font-weight: bold; }
        .stTextInput>div>div>input, .stSelectbox>div>div>select { background-color: #e0e7ff; color: #1f2937; }
        .stDataFrame { background-color: #e0e7ff; padding: 1rem; border-radius: 5px; overflow-x: auto; }
        .dataframe { color: #1f2937; width: 100%; }
        h1, h2, h3 { color: #4CAF50; }
        .review-text { color: #ffffff; background-color: rgba(0, 0, 0, 0.6); padding: 10px; border-radius: 5px; margin-bottom: 10px; }
        .review-rating { color: #FFD700; font-weight: bold; }
        @media (max-width: 768px) { .dataframe { font-size: 0.8em; } }
        .stSlider [data-baseweb="slider"] { color: #FFFFFF !important; }
        .date-time-box { background-color: #4CAF50; color: #FFFFFF; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
        .disclaimer { font-size: 0.8em; color: #888888; margin-top: 20px; }
        </style>
        """, unsafe_allow_html=True)
    
    st.title("Food Dining Options Nearby")
    
    global gmaps
    gmaps = get_gmaps_client()
    if not gmaps:
        st.error("Failed to initialize Google Maps client. Please check your API key.")
        st.stop()
    
    col1, col2 = st.columns([2, 1])
    with col1:
        address = st.text_input("Enter your address:", placeholder="Enter your address here")
    with col2:
        radius = st.slider("Search radius (in meters)", 500, 5000, 1000, step=100)
    
    if address:
        with st.spinner("Fetching nearby food options..."):
            lat, lng = get_coordinates(address)
            if lat and lng:
                places = get_nearby_food_places(lat, lng, radius)
                
                if places:
                    st.subheader("Map")
                    m = create_map(lat, lng, places)
                    folium_static(m, width=1300, height=500)
                    
                    st.subheader("Food Options")
                    
                    # Add date and time box
                    current_time = datetime.now(pytz.timezone('Asia/Singapore'))
                    st.markdown(f"""
                    <div class="date-time-box">
                        Current Date and Time: {current_time.strftime("%Y-%m-%d %H:%M:%S")}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    place_data = []
                    place_details = {}
                    for place in places:
                        try:
                            details = get_place_details(place['place_id'])
                            place_details[place['place_id']] = details
                            distance = calculate_distance((lat, lng), (place['geometry']['location']['lat'], place['geometry']['location']['lng']))
                            open_status = is_open_now(details.get('opening_hours', {}))
                            place_data.append({
                                'Name': place['name'],
                                'Rating': details.get('rating', 'N/A'),
                                'Price Level': '$' * details.get('price_level', 0) or 'N/A',
                                'Type': ', '.join(details.get('types', [])) or 'N/A',
                                'Distance': distance,
                                'Open Now': open_status,
                                'Place ID': place['place_id'],
                                'Number of Reviews': details.get('user_ratings_total', 0)
                            })
                        except Exception as e:
                            st.error(f"Error processing place {place['name']}: {str(e)}")
                            continue
                    
                    df = pd.DataFrame(place_data).drop_duplicates(subset=['Name', 'Distance'], keep='first')
                    
                    # Filtering options
                    st.sidebar.subheader("Filter Options")
                    min_rating = st.sidebar.slider("Minimum Rating", 0.0, 5.0, 0.0, 0.1)
                    max_price = st.sidebar.selectbox("Maximum Price Level", ['Any', '$', '$$', '$$$', '$$$$'])
                    open_status_filter = st.sidebar.multiselect("Open Status", ["Open", "Closed", "Unknown"], default=["Open", "Unknown"])
                    cuisine_types = list(set([cuisine for place in df['Type'].str.split(', ') for cuisine in place]))
                    selected_cuisines = st.sidebar.multiselect("Cuisine Type", cuisine_types)
                    
                    # Apply filters
                    df_filtered = df.copy()
                    df_filtered['Rating'] = pd.to_numeric(df_filtered['Rating'], errors='coerce')
                    df_filtered = df_filtered[
                        (df_filtered['Rating'] >= min_rating) &
                        (df_filtered['Open Now'].isin(open_status_filter)) &
                        (df_filtered['Type'].apply(lambda x: any(cuisine in x for cuisine in selected_cuisines)) if selected_cuisines else True)
                    ]
                    
                    if max_price != 'Any':
                        df_filtered = df_filtered[df_filtered['Price Level'].str.len() <= len(max_price)]
                    
                    if df_filtered.empty:
                        st.warning("No results match your current filters. Try adjusting the filters.")
                    else:
                        sort_option = st.selectbox("Sort by:", ["Distance", "Price Level", "Rating", "Number of Reviews"])
                        if sort_option == "Distance":
                            df_filtered = df_filtered.sort_values("Distance")
                        elif sort_option == "Price Level":
                            df_filtered['Price Level'] = df_filtered['Price Level'].str.len()
                            df_filtered = df_filtered.sort_values("Price Level")
                            df_filtered['Price Level'] = df_filtered['Price Level'].apply(lambda x: '$' * x if x != 'N/A' else x)
                        elif sort_option == "Rating":
                            df_filtered = df_filtered.sort_values("Rating", ascending=False)
                        else:
                            df_filtered = df_filtered.sort_values("Number of Reviews", ascending=False)
                        
                        df_filtered['Rating'] = df_filtered['Rating'].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else 'N/A')
                        st.dataframe(df_filtered.drop(columns=['Place ID']).style.set_properties(**{'background-color': '#e0e7ff', 'color': '#1f2937'}))
                        
                        selected_place = st.selectbox("Select a place for more details:", df_filtered['Name'])
                        
                        if selected_place:
                            selected_place_id = df_filtered[df_filtered['Name'] == selected_place]['Place ID'].values[0]
                            details = place_details[selected_place_id]
                            
                            st.subheader(f"Details for {selected_place}")
                            
                            detailed_data = {
                                'Details': [
                                    details.get('formatted_address', 'N/A'),
                                    details.get('formatted_phone_number', 'N/A'),
                                    details.get('website', 'N/A'),
                                    '\n'.join(details.get('opening_hours', {}).get('weekday_text', ['N/A'])),
                                    ', '.join(details.get('types', ['N/A'])),
                                    f"{details.get('rating', 'N/A')}",
                                    '$' * details.get('price_level', 0) or 'N/A',
                                    details.get('user_ratings_total', 'N/A')
                                ]
                            }
                            
                            detailed_df = pd.DataFrame(detailed_data, index=['Address', 'Phone', 'Website', 'Opening Hours', 'Types', 'Rating', 'Price Level', 'Number of Reviews'])
                            st.dataframe(detailed_df.style.set_properties(**{'background-color': '#e0e7ff', 'color': '#1f2937', 'white-space': 'pre-wrap', 'word-wrap': 'break-word'}))
                            
                            st.subheader("Reviews")
                            if 'reviews' in details:
                                reviews = sorted(details['reviews'], key=lambda x: x['rating'], reverse=True)
                                positive_reviews = [r for r in reviews if r['rating'] >= 4][:3]
                                negative_reviews = [r for r in reviews if r['rating'] <= 2][-3:]
                                
                                st.markdown("### Top Positive Reviews")
                                if positive_reviews:
                                    for review in positive_reviews:
                                        st.markdown(f"<p class='review-rating'>Rating: {'⭐' * int(review['rating'])}</p>", unsafe_allow_html=True)
                                        st.markdown(f"<div class='review-text'>{review['text']}</div>", unsafe_allow_html=True)
                                else:
                                    st.write("No positive reviews available.")
                                
                                st.markdown("### Top Negative Reviews")
                                if negative_reviews:
                                    for review in negative_reviews:
                                        st.markdown(f"<p class='review-rating'>Rating: {'⭐' * int(review['rating'])}</p>", unsafe_allow_html=True)
                                        st.markdown(f"<div class='review-text'>{review['text']}</div>", unsafe_allow_html=True)
                                else:
                                    st.write("No negative reviews available.")
                            else:
                                st.write("No reviews available for this place.")
                else:
                    st.warning("No food options found in the specified radius. Try increasing the search radius.")
            else:
                st.error("Unable to find coordinates for the given address. Please check the address and try again.")
    
    # Add disclaimer
    st.sidebar.markdown("""
    <div class="disclaimer">
    This app uses the Google Maps API, and was generated with the aid of GenAI + Human Creativity!
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        st.error("Please try refreshing the page or contact support if the issue persists.")