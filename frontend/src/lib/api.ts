export async function analyze(title: string, price: number) {
  const response = await fetch("http://127.0.0.1:8000/analyze", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title,
      price,
    }),
  });

  if (!response.ok) {
    throw new Error("Request failed");
  }

  return response.json();
}