import Navbar from '../../components/Navbar/Navbar';
import Hero from '../../components/Hero/Hero';
import FeatureHighlights from '../../components/FeatureHighlights/FeatureHighlights';
import CTABanner from '../../components/CTABanner/CTABanner';
import Footer from '../../components/Footer/Footer';

export default function Home() {
  return (
    <>
      <Navbar transparent />
      <main>
        <Hero />
        <FeatureHighlights />
        <CTABanner />
      </main>
      <Footer />
    </>
  );
}
