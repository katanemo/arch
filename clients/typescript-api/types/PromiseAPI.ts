import { ResponseContext, RequestContext, HttpFile, HttpInfo } from '../http/http';
import { Configuration} from '../configuration'

import { CreateEmbeddingRequest } from '../models/CreateEmbeddingRequest';
import { CreateEmbeddingRequestInput } from '../models/CreateEmbeddingRequestInput';
import { CreateEmbeddingRequestModel } from '../models/CreateEmbeddingRequestModel';
import { CreateEmbeddingResponse } from '../models/CreateEmbeddingResponse';
import { CreateEmbeddingResponseUsage } from '../models/CreateEmbeddingResponseUsage';
import { Embedding } from '../models/Embedding';
import { ObservableEmbeddingsApi } from './ObservableAPI';

import { EmbeddingsApiRequestFactory, EmbeddingsApiResponseProcessor} from "../apis/EmbeddingsApi";
export class PromiseEmbeddingsApi {
    private api: ObservableEmbeddingsApi

    public constructor(
        configuration: Configuration,
        requestFactory?: EmbeddingsApiRequestFactory,
        responseProcessor?: EmbeddingsApiResponseProcessor
    ) {
        this.api = new ObservableEmbeddingsApi(configuration, requestFactory, responseProcessor);
    }

    /**
     * Creates an embedding vector representing the input text.
     * @param createEmbeddingRequest 
     */
    public createEmbeddingWithHttpInfo(createEmbeddingRequest: CreateEmbeddingRequest, _options?: Configuration): Promise<HttpInfo<CreateEmbeddingResponse>> {
        const result = this.api.createEmbeddingWithHttpInfo(createEmbeddingRequest, _options);
        return result.toPromise();
    }

    /**
     * Creates an embedding vector representing the input text.
     * @param createEmbeddingRequest 
     */
    public createEmbedding(createEmbeddingRequest: CreateEmbeddingRequest, _options?: Configuration): Promise<CreateEmbeddingResponse> {
        const result = this.api.createEmbedding(createEmbeddingRequest, _options);
        return result.toPromise();
    }


}



