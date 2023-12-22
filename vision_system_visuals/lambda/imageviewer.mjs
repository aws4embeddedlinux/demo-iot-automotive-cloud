
import {GetObjectCommand, S3Client} from "@aws-sdk/client-s3";
import {
    getSignedUrl,
} from "@aws-sdk/s3-request-presigner";

const REGION=process.env.REGION;
console.log(REGION)
export const handler = async (event) => {
    console.log(event)
    let pathParam = event.path;
    if (pathParam) {
        pathParam = pathParam.slice(1);
    }
    const bucketString = pathParam.replace("s3://", "");
    const bucketName = bucketString.split('/', 1)[0];
    const objectKey = bucketString.substring(bucketString.indexOf('/') + 1, bucketString.length);
    let clientUrl = null;
    if (bucketName && objectKey) {
        try {
            clientUrl = await createPresignedUrlWithClient({
                region: REGION,
                bucket: bucketName,
                key: objectKey,
            });
        } catch (error) {
            console.error(error)
            return {
                statusCode: 400,
                body: `Cannot process event: ${error}`,
            }
        }
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'text/html',
            },
            body:
                `<html><body><img src="${clientUrl}" width="800" /></body></html>`
        }
    }
}
const createPresignedUrlWithClient = ({region, bucket, key}) => {
    const client = new S3Client({region});
    const command = new GetObjectCommand({Bucket: bucket, Key: key});
    return getSignedUrl(client, command, {expiresIn: 30600});
};
