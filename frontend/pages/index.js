import { useState, useEffect } from "react";
import axios from "axios";
import Filters from "../components/Filters";
import ListingCard from "../components/ListingCard";

export default function Home() {

  const [listings, setListings] = useState([]);
  const [query, setQuery] = useState("toyota");

  const fetchListings = async () => {
    const res = await axios.get(`http://carmates-scraper.vercel.app/search?q=${query}`);
    setListings(res.data);
  };

  useEffect(() => {
    fetchListings();
  }, []);

  return (
    <div style={{padding:20}}>
      <h1>CarMates AU Dashboard</h1>

      <Filters setQuery={setQuery} fetchListings={fetchListings} />

      <div style={{display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:20}}>
        {listings.map((l, i) => (
          <ListingCard key={i} listing={l} />
        ))}
      </div>
    </div>
  );
}
