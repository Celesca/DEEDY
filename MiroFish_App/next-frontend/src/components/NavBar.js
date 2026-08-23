'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function NavBar() {
  const pathname = usePathname();

  const navItems = [
    { name: 'Command Center', path: '/' },
    { name: 'Analytics', path: '/analytics' },
    { name: 'Agents', path: '/agents' },
    { name: 'Reports', path: '/reports' },
  ];

  return (
    <nav className="glass-panel" style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '12px 24px',
      margin: '24px 24px 0 24px',
      borderRadius: '24px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{
          width: '32px', height: '32px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-magenta))',
          boxShadow: '0 0 15px rgba(160, 196, 255, 0.4)'
        }}></div>
        <h1 style={{ fontSize: '1.2rem', fontWeight: '600', letterSpacing: '0.5px', color: '#fff' }}>
          MiroFish<span style={{ color: 'var(--text-secondary)' }}> Simulator</span>
        </h1>
      </div>
      <div style={{ display: 'flex', gap: '8px' }}>
        {navItems.map(item => {
          const isActive = pathname === item.path;
          return (
            <Link key={item.path} href={item.path} style={{
              padding: '8px 16px',
              borderRadius: '12px',
              textDecoration: 'none',
              color: isActive ? '#fff' : 'var(--text-secondary)',
              background: isActive ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
              fontWeight: isActive ? '500' : '400',
              transition: 'all 0.2s ease'
            }}>
              {item.name}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
