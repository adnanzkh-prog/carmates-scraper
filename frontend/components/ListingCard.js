export default function ListingCard({ listing }) {

  return (
    <div style={{border:"1px solid #ddd", padding:10}}>

      <h3>{listing.title}</h3>

      <p><b>${listing.price}</b></p>

      <p>{listing.description.slice(0,100)}...</p>

      <a href={listing.url} target="_blank">View</a>

      {listing.contact_numbers.length > 0 && (
        <p>📞 {listing.contact_numbers.join(", ")}</p>
      )}

    </div>
  );
}
