import "./globals.css";
import { SimulationProvider } from '../context/SimulationContext';
import NavBar from '../components/NavBar';

export const metadata = {
  title: "MiroFish Command Center",
  description: "AI Social Simulation Engine",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <SimulationProvider>
          <NavBar />
          <main style={{ padding: '24px', height: 'calc(100vh - 100px)', overflow: 'hidden' }}>
            {children}
          </main>
        </SimulationProvider>
      </body>
    </html>
  );
}
