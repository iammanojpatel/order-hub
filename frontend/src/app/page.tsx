import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <h1>App</h1>
      <p>Reference implementation: DDD backend, typed contract, server-first React.</p>
      <Link href="/products">Go to products →</Link>
    </main>
  );
}
