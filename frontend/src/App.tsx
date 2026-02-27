import { Layout } from './components/Layout/Layout';
import { ModeProvider } from './contexts/ModeContext';

function App() {
  return (
    <ModeProvider>
      <Layout />
    </ModeProvider>
  );
}

export default App;
