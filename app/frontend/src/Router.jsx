import { BrowserRouter, Routes, Route } from 'react-router-dom';
import App from './App';
import XuLangPage from './XuLangPage';

export default function Router() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/xulang" element={<XuLangPage />} />
      </Routes>
    </BrowserRouter>
  );
}
