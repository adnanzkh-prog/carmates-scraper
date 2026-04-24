export default function Filters({ setQuery, fetchListings }) {

  return (
    <div style={{marginBottom:20}}>
      <input
        placeholder="Search (e.g Toyota Corolla)"
        onChange={(e)=>setQuery(e.target.value)}
      />
      <button onClick={fetchListings}>Search</button>
    </div>
  );
}
