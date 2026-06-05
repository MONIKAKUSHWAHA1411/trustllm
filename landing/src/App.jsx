import AnnouncementBanner from './components/AnnouncementBanner';
import Navbar            from './components/Navbar';
import Hero              from './components/Hero';
import HowItWorks        from './components/HowItWorks';
import ModelsSection     from './components/ModelsSection';
import FeatureCards      from './components/FeatureCards';
import TrustedBy         from './components/TrustedBy';
import CTASection        from './components/CTASection';
import Footer            from './components/Footer';

export default function App() {
  return (
    <div style={{ fontFamily: 'Inter, system-ui, sans-serif', backgroundColor: '#FFFFFF', margin: 0, padding: 0 }}>
      <AnnouncementBanner />
      <Navbar />
      <main>
        <Hero />
        <HowItWorks />
        <ModelsSection />
        <FeatureCards />
        <TrustedBy />
        <CTASection />
      </main>
      <Footer />
    </div>
  );
}
