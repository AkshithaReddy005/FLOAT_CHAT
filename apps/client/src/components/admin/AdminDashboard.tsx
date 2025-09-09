import { Layout } from '../common/Layout';
import { FileUpload } from './FileUpload';
import { useUpload } from '../../hooks/useUpload';

export const AdminDashboard = () => {
  const { status, uploadFile } = useUpload();

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      uploadFile(file);
    }
  };

  return (
    <Layout title="Admin Dashboard">
      <FileUpload onFileChange={handleFileChange} status={status} />
    </Layout>
  );
};