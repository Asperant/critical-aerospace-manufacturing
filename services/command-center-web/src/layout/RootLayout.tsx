import { Outlet } from "react-router-dom";

export function RootLayout() {
  return (
    <>
      <header>
        <strong>Manufacturing Command Center</strong>
      </header>
      <main>
        <Outlet />
      </main>
    </>
  );
}
