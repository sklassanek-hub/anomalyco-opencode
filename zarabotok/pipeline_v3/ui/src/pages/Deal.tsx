import { useParams } from 'react-router-dom';
import DocumentTitle from '../components/DocumentTitle';
import DealDetail from '../components/DealDetail';

export default function DealPage() {
  const { id } = useParams<{ id: string }>();
  if (!id) return <div className="page">Сделка не указана</div>;
  return (
    <div className="page">
      <DocumentTitle title="Сделка" />
      <div className="page-head">
        <h1>Сделка</h1>
        <p className="muted mono">{decodeURIComponent(id)}</p>
      </div>
      <DealDetail dealId={decodeURIComponent(id)} />
    </div>
  );
}